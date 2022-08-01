# GovDiagnose
```shell
nohup python3 main_test.py > /dev/null 2>&1 &
ps -ef | grep main_test | grep -v grep | awk '{print "kill -9 "$2}' | sh
pid:6024
```
1. 将wb.text.model开头的三个文件放到data文件夹下