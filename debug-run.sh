rm debug.log
rm errors.log
python3 main.py --debug $1 > debug.log 2>&1 &
wait
echo "**Broswer warnings BELOW**: " > errors.log
cat debug.log | grep WARNING >> errors.log
echo "**Render-level errors BELOW** " >> errors.log
cat debug.log | grep ERROR >> errors.log
echo "**Python-level errors BELOW - LIKELY AT LEAST SOMEWHAT SEVERE**" >> errors.log
cat debug.log | grep Error >> errors.log
