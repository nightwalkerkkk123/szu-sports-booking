#!/usr/bin/env bash
# szu-sports-booking skill \u52a0\u8f7d\u811a\u672c (bash / zsh / Git Bash)
#
# \u7528\u6cd5: source scripts/load_env.sh
# (\u6ce8\u610f\u662f source, \u4e0d\u662f\u6267\u884c, \u8981\u8ba9 env \u751f\u6548\u5728\u5f53\u524d shell)
#
# \u4f1a\u52a0\u8f7d .agents/skills/szu-sports-booking/.env \u5230\u5f53\u524d shell \u73af\u5883\u53d8\u91cf
# \u8fd9\u6837 booking api \u547d\u4ee4\u5c31\u80fd\u81ea\u52a8\u8bfb\u5230\u51ed\u8bc1, \u4e0d\u9700\u8981 -p \u53c2\u6570

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$SKILL_DIR/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "[X] \u672a\u627e\u5230 $ENV_FILE" >&2
    echo "  \u8bf7\u5148\u590d\u5236 .env.example \u4e3a .env \u5e76\u586b\u5165\u51ed\u8bc1:" >&2
    echo "    cp $SKILL_DIR/.env.example $ENV_FILE" >&2
    return 1 2>/dev/null || exit 1
fi

# \u52a0\u8f7d KEY=VALUE (\u8df3\u8fc7\u7a7a\u884c\u548c\u6ce8\u91ca)
COUNT=0
while IFS= read -r line; do
    # \u53bb\u6389\u9996\u5c3e\u7a7a\u767d
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    # \u8df3\u8fc7\u7a7a\u884c\u548c\u4ee5 # \u5f00\u5934\u7684\u6ce8\u91ca
    [ -z "$line" ] && continue
    [[ "$line" == \#* ]] && continue
    # \u89e3\u6790 KEY=VALUE
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
        key="${BASH_REMATCH[1]}"
        value="${BASH_REMATCH[2]}"
        # \u53bb\u6389\u5305\u88f9\u7684\u5f15\u53f7
        if [[ "$value" =~ ^\"(.*)\"$ ]] || [[ "$value" =~ ^\'(.*)\'$ ]]; then
            value="${BASH_REMATCH[1]}"
        fi
        export "$key"="$value"
        COUNT=$((COUNT + 1))
    fi
done < "$ENV_FILE"

echo "[OK] \u5df2\u52a0\u8f7d $COUNT \u4e2a\u73af\u5883\u53d8\u91cf\u4ece $ENV_FILE" >&2
[ -n "$SZU_USERNAME" ] && echo "     SZU_USERNAME=$SZU_USERNAME" >&2
if [ -n "$SZU_USERNAME" ]; then
    SUFFIX="${SZU_USERNAME: -4}"
    PWD_KEY="SZU_PASSWORD_$SUFFIX"
    if [ -n "${!PWD_KEY}" ]; then
        echo "     $PWD_KEY=********" >&2
    fi
fi
