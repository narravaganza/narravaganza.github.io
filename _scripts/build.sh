set -ex
hugo --cleanDestinationDir --destination docs

if [ "$1" == "-s" ]; then
    pkill -f "hugo serve" || true
    hugo serve \
        --destination docs \
        --disableFastRender
fi
