#!/bin/zsh
# best-base.sh PLAYS_FILE ARISTOTLE_PATH : the Aristotle commit (or the CPR fork) whose copy is nearest the plays' copy
pf=$1; ap=$2; T=$(mktemp -d)
best=999999; bc=none
for c in $(git -C ~/Developer/aristotle-reader log --format=%h de57f687c6 -- $ap); do
  git -C ~/Developer/aristotle-reader show $c:$ap > $T/a 2>/dev/null || continue
  n=$(git diff --no-index --numstat $pf $T/a | awk '{print $1+$2}'); n=${n:-0}
  if (( n < best )); then best=$n; bc=$c; fi
done
git -C ~/Developer/classical-philosophy-reader show 233ec2547a:$ap > $T/a 2>/dev/null && { n=$(git diff --no-index --numstat $pf $T/a | awk '{print $1+$2}'); n=${n:-0}; (( n < best )) && { best=$n; bc=cpr:233ec2547a; } }
echo "$ap $bc $best $( [[ $bc != cpr* && $bc != none ]] && git -C ~/Developer/aristotle-reader log -1 --format=%ad --date=short $bc)"
rm -rf $T
