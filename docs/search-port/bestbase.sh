#!/bin/zsh
# best-base.sh PLAYS_FILE ARISTOTLE_PATH : the Aristotle commit (or the CPR fork) whose copy is nearest the plays' copy
pf=$1; ap=$2; T=$(mktemp -d)
[[ -r $pf ]] || { echo "cannot read $pf" >&2; exit 1; }
# Distance = lines added + removed; identical files print no numstat, which is 0.
dist() { cmp -s $1 $2 && { echo 0; return; }; local n=$(git diff --no-index --numstat $1 $2 | awk '{print $1+$2}'); [[ -n $n ]] || { echo "diff failed: $1 $2" >&2; exit 1; }; echo $n; }
best=999999; bc=none
for c in $(git -C ~/Developer/aristotle-reader log --format=%h de57f687c6 -- $ap); do
  git -C ~/Developer/aristotle-reader show $c:$ap > $T/a 2>/dev/null || continue
  n=$(dist $pf $T/a) || exit 1
  if (( n < best )); then best=$n; bc=$c; fi
done
git -C ~/Developer/classical-philosophy-reader show 233ec2547a:$ap > $T/a 2>/dev/null && { n=$(dist $pf $T/a) || exit 1; (( n < best )) && { best=$n; bc=cpr:233ec2547a; } }
echo "$ap $bc $best $( [[ $bc != cpr* && $bc != none ]] && git -C ~/Developer/aristotle-reader log -1 --format=%ad --date=short $bc)"
rm -rf $T
