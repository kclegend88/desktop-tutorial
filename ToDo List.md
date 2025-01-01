# ToDo List

### Important

- [ ] prc_monitor: check all prc status and restart thread if nessecary

- [ ] exit cleanup: before main() close, clean sys: ready in redis, and all streams 

- [ ] xadd or file-io, save logger info, sync to DSS database or write into local path. 

- [ ] put all radio I/O, snap 7 I/O into try-exception, and catch the exception to avoit thread dead-lock

- [ ] Dashboard DataBase Plan

- [ ] plc connection fault -- alarm and stop

### Urgent

- [ ] PLC Comm process, read-write, record trigger-->stm
- [ ] DSS Comm process, stm_RC--> DSS Database
- [ ] DSS: status transfer process, transfer log(reason, ts, status before/after)
- [ ] 
- [ ] - [ ] SRF prc plan :  RFID, stmRFID_data, PLC, 
- [ ] DRF prc plab

### Just ToDo

- [ ] cli_template, entrance with cli_id, independent redis connection

- [ ] Test: when start main_cli.py  twice, how many logger instance? independent or unique ?

- [ ] prc_template , function, init, cycletime, exit by run-lock, exit by exit command, exit by exception....

- [ ] MAWB data prepare, 2 MAWB, 1 with barcode + EPC(300 pcs, 7-8 box) , 1 with barcode, without EPC, 250, 5 box; 

- [ ] log level test, log rotation test, copy rotated log to syncthing file path;

- [ ] plc_conv, data_type replan, no need: is lock, avoid continue start-stop

- [ ] All stream change to read-ack loop, check pending when restart;