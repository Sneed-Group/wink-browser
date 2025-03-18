rm debug.log
rm errors.log
python3 main.py > debug.log 2>&1 &
wait
cat debug.log | grep WARNING > errors.log
cat debug.log | grep ERROR >> errors.log

