#!/bin/bash
# bash fix_tabs.sh
# ממיר 4 רווחים בתחילת שורה ל-TAB אמיתי
sed -i 's/^    /\t/' Makefile

# ממיר 8 רווחים בתחילת שורה ל-TAB (ליתר ביטחון)
sed -i 's/^        /\t/' Makefile

# ממיר 2 רווחים בתחילת שורה ל-TAB (רק אם זה בתחילת שורה)
sed -i 's/^  /\t/' Makefile
