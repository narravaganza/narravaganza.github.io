set -ex
python3 scripts/optimize-images.py
hugo --cleanDestinationDir --destination docs

if [ "$1" == "-s" ]; then
    pkill -f "hugo serve" || true
    hugo serve \
        --destination tmp \
        --disableFastRender
fi
