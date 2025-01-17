# prc_template  v 0.3.0
import json
import threading
import time
import datetime

from fLog import clsLogger
from fConfig import clsConfig
from fConfigEx import clsConfigEx
from fRedis import clsRedis
from fHIKCamera import clsHIKCameraClient



def start_process(config_file):
    def prc_stmMS_dataproc(lstdata):
        for i,dictdata in l[0][1]:             # 遍历收到的所有消息
            # inst_redis.sadd("set_ms", dictdata['barcode'])     # 将条码加入set_manualscan
            # 将条码发送给barcode check 模块
            # 如果返回的是各类异常 BL/OP/NF/SF/RC,那么需要反馈barcode check 异常，要求客户端执行剔除操作
        
            # 如果返回的是ok，那么仅仅进行扫描补码，补码条件满足就恢复输送机运行
            if dictdata['type'] == 'MR':
                inst_redis.sadd("set_ms_mr", dictdata['barcode'])     
            elif dictdata['type'] == 'NR':
                inst_redis.sadd("set_ms_nr", dictdata['barcode'])   
            else:
                inst_logger.error("线程 %s 中, prc_stmMS_dataproc 数据时发现数据类型异常: 补码类型不为MR或NR" %(__prc_name__,))
                continue
        lst_reading_nr = list(inst_redis.getset("set_reading_nr"))  # 更新set_reading_nr
        lst_ms_nr = list(inst_redis.getset("set_ms_nr"))            # 更新set_ms_nr       
        set_reading_mr = inst_redis.getset("set_reading_mr")  # 更新set_reading_mr
        set_ms_mr = inst_redis.getset("set_ms_mr")            # 更新set_ms_mr    
        
        if len(lst_reading_nr) + len(set_reading_mr) == 0:
            return
        # 开始逻辑判断
        # set_ms_nr 的数量，与set_reading_nr的数量一致
        if not len(lst_ms_nr)== len(lst_reading_nr):
            return
        # set_ms_mr 的 set_reading_mr 完全一致
        if not set_ms_mr == set_reading_mr:
            return
        # 所有read_ng的包裹都已经被捕捉
        # 将read_nr/mr中的所有包裹，从set_reading mr/nr中删除，移动到set_reading_gr中，parcel:status更改成为mr_ms或者nr_ms

        for i,parcel_uid in enumerate(lst_reading_nr):
            inst_redis.setkey(f"parcel:scan_result:{parcel_uid}","NR_MS")
            inst_redis.setkey(f"parcel:barcode:{parcel_uid}",lst_ms_nr[i])
            inst_logger.info("包裹补码成功,线程 %s 修改NR包裹状态 uid= %s, barcode =%s"%(__prc_name__,parcel_uid,lst_ms_nr[i]))
        inst_redis.clearset("set_ms_nr")
        inst_redis.clearset("set_reading_nr")
            
        for parcel_barcode in set_reading_mr:
            parcel_uid = inst_redis.getkey(f"parcel:ms_barcode:{parcel_barcode}")
            inst_redis.setkey(f"parcel:scan_result:{parcel_uid}","MR_MS")
            inst_redis.setkey(f"parcel:barcode:{parcel_uid}",parcel_barcode)
            inst_logger.info("包裹补码成功,线程 %s 修改MR包裹状态 uid= %s, barcode =%s"%(__prc_name__,parcel_uid,parcel_barcode))
        inst_redis.clearset("set_ms_mr")       
        inst_redis.clearset("set_reading_mr")

        # 恢复输送机速度
        plc_conv_status = inst_redis.getkey("plc_conv:status")
        plc_conv_fullspeed = inst_redis.getkey("plc_conv:fullspeed")
        if plc_conv_status == 'run':
            if plc_conv_fullspeed == 'countdown':
                inst_redis.setkey("plc_conv:command",'autospeedup')
                inst_logger.info("包裹补码成功，线程 %s 尝试将输送机恢复至正常速度" %(__prc_name__,))
            else:
                inst_logger.error("线程 %s 在恢复输送机速度时发现状态异常" %(__prc_name__,))
                return
        else:
            inst_redis.setkey("plc_conv:command",'start')       # 如果不在运转，则说明已停机，需重新启动
            inst_logger.info("包裹补码成功，线程 %s 尝试重新启动输送机" %(__prc_name__,))


    __prc_name__="stmManualScan"                      
    
    ini_config = clsConfig(config_file)     # 来自主线程的配置文件
    inst_logger = clsLogger(ini_config)     # 实际上与主线程使用的是同一实例
    inst_redis = clsRedis(ini_config)       # 实际上与主线程使用的是同一实例

    inst_logger.info("线程 %s 正在启动" %(__prc_name__,))

    # 本地ini文件读取
    str_ini_file_name = "prc_%s.ini" %(__prc_name__,)
    __ini_prc_config__=clsConfigEx(str_ini_file_name)
    __prc_cycletime=__ini_prc_config__.CycleTime.prc_cycletime
    __prc_expiretime=__ini_prc_config__.CycleTime.prc_expiretime
    __prc_healthytime=__ini_prc_config__.CycleTime.prc_healthytime

    # --------------------    
    # 定制化配置参数读取区

    # 定制化配置参数读取区
    # --------------------
   
    # 系统将初始化信息写入Redis
    __prc_id__ = inst_redis.init_prc(__prc_name__,__prc_expiretime)
    if not __prc_id__:  # 取得异常消息队列中的信息
        for i, e in enumerate(inst_redis.lstException):
            inst_logger.error(
                "线程 %s 注册 Redis 服务器失败，调用模块 %s，调用时间 %s，异常信息 %s "
                % (__prc_name__,e['module'], e['timestamp'], e['msg']))
        inst_redis.lstException.clear()
        return       # Redis 注册失败失败

    # --------------------    
    # 以下为定制初始化区域
    if not inst_redis.xcreategroup("stream_manualscan", "manualscan"):
        inst_logger.info("线程 %s 注册stream组失败，该组已存在" %("manualscan",))
    else:
        inst_logger.info("线程 %s 注册stream组成功" %("manualscan",))
    dictdata={}
    lstdictdata=[]
    set_reading_mr={}
    lst_reading_nr=[]
    set_ms_mr={}
    lst_ms_nr=[]
    # 以上为定制初始化区域           
    # --------------------    

    # 主线程变量初始化：启动变量，退出返回值
    b_thread_running = True
    int_exit_code = 0


    while b_thread_running:
        # 刷新当前线程的运行锁
        inst_redis.setkeypx(f"pro_mon:{__prc_name__}:run_lock",__prc_id__,__prc_expiretime)
        # --------------------
        # 以下为主线程操作区
        l = inst_redis.xreadgroup("stream_manualscan","manualscan","manualscan-id01")
        if len(l)>0 :                       # 收到消息
            prc_stmMS_dataproc(l[0][1])
        # 以上为主线程操作区       
        # --------------------
        time.sleep(__prc_cycletime/1000.0)  # 所有时间均以ms形式存储
        
        # 线程运行时间与健康程度判断
        inst_redis.ct_refresh(__prc_name__)
        # ToDo
        
                
        # 线程是否继续运行的条件判断
        
        #如线程运行锁过期或被从外部删除，则退出线程
        prc_run_lock=inst_redis.getkey(f"pro_mon:{__prc_name__}:run_lock")
        if prc_run_lock is None:  
            # --------------------
            # 以下为定制区域，用于中止线程内创建的线程或调用的函数
            inst_redis.xdelgroup("stream_test", "HIKC_data")
            for i, e in enumerate(inst_redis.lstException):
                inst_logger.error(
                    "线程 %s 超时退出时发生 Redis 异常，调用模块 %s，调用时间 %s，异常信息 %s "
                    % (__prc_name__,e['module'], e['timestamp'], e['msg']))
            inst_redis.lstException.clear()
            inst_logger.info("线程 %s 删除stream组成功" %("HIKC_data",))
            # 以上为定制区域，用于中止线程内创建的线程或调用的函数           
            # --------------------
            int_exit_code = 1
            break
        
        #如command区收到退出命令，根据线程类型决定是否立即退出
        prc_run_lock=inst_redis.getkey(f"pro_mon:{__prc_name__}:command")
        if prc_run_lock == "exit":
            # 在此处判断是否有尚未完成的任务，或尚未处理的stm序列；
            # 如有则暂缓退出，如没有立即退出
            
            inst_redis.xdelgroup("stream_test", "HIKC_data")
            inst_logger.info("线程 %s 删除stream组成功" %("HIKC_data",))
            for i, e in enumerate(inst_redis.lstException):
                inst_logger.error(
                    "线程 %s 受控退出时发生 Redis 异常，调用模块 %s，调用时间 %s，异常信息 %s "
                    % (__prc_name__,e['module'], e['timestamp'], e['msg']))
            inst_redis.lstException.clear()
            int_exit_code = 2
            break
    
    inst_logger.info("线程 %s 已退出，返回代码为 %d" %(__prc_name__,int_exit_code))

