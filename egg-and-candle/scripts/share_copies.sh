#!/usr/bin/env bash
# Share copies of the full render: one whole-film file and one file per page,
# each under 30 MiB (the chat upload limit), 1080p H.264 + AAC, faststart.
set -euo pipefail
cd "$(dirname "$0")/.."
M=renders/egg-and-candle.mp4
OUT=renders/share
mkdir -p "$OUT"
LIMIT=$((29 * 1024 * 1024))   # stay a little under 30 MiB

# two-pass H.264 at a bitrate that fits `limit` bytes over `dur` seconds (audio 128k)
fit() { # in out ss dur [scale] [abr] [preset]
  local in=$1 out=$2 ss=$3 dur=$4 scale=${5:-} abr=${6:-128} preset=${7:-medium}
  local vk=$(( (LIMIT * 8 / 1000) / (${dur%.*} + 1) - abr - 20 ))
  local vf="format=yuv420p"
  [ -n "$scale" ] && vf="scale=$scale:flags=lanczos,format=yuv420p"
  local af="afade=t=in:st=0:d=0.3,afade=t=out:st=$(python3 -c "print(max(0,$dur-0.8))"):d=0.8"
  ffmpeg -loglevel error -y -ss "$ss" -t "$dur" -i "$in" -vf "$vf" -c:v libx264 -preset $preset -b:v ${vk}k -maxrate $((vk * 2))k -bufsize $((vk * 4))k \
    -pass 1 -passlogfile "$OUT/pass" -an -f mp4 /dev/null
  ffmpeg -loglevel error -y -ss "$ss" -t "$dur" -i "$in" -vf "$vf" -c:v libx264 -preset $preset -b:v ${vk}k -maxrate $((vk * 2))k -bufsize $((vk * 4))k \
    -pass 2 -passlogfile "$OUT/pass" -af "$af" -c:a aac -b:a ${abr}k -movflags +faststart "$out"
  echo "$out: video ${vk}k, $(stat -c %s "$out") bytes"
}

# per page: from where the page's sheet lands to where the next page's sheet lands
starts=(0 54.3 114.6 178.3 232.9 309.1)
for i in 0 1 2 3 4; do
  ss=${starts[$i]}; end=${starts[$((i + 1))]}
  dur=$(python3 -c "print(round($end - $ss, 2))")
  fit "$M" "$OUT/egg-and-candle-page$((i + 1)).mp4" "$ss" "$dur"
done
# the whole film
fit "$M" "$OUT/egg-and-candle-full.mp4" 0 309.1 "" 112 slow
rm -f "$OUT"/pass*
ls -la "$OUT"
