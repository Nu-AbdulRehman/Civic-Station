#!/bin/sh
# Build both images once, tag them, push every tag (T-M8-009, T-M8-011, ADR-0003).
#   scripts/publish-images.sh <registry> <tag> [<tag>...]
# The first tag is the one digests are reported for. With GITHUB_OUTPUT set, writes
# backend_digest= and frontend_digest= as step outputs. The caller must already be logged in.
set -eu

REGISTRY=$1
shift
for svc in backend frontend; do
    repo=$REGISTRY/civic-station-$svc
    docker build -t "$repo:$1" "$svc"
    for tag in "$@"; do
        [ "$tag" = "$1" ] || docker tag "$repo:$1" "$repo:$tag"
        docker push "$repo:$tag"
    done
    digest=$(docker image inspect -f '{{index .RepoDigests 0}}' "$repo:$1")
    echo "$svc: $digest"
    [ -z "${GITHUB_OUTPUT:-}" ] || echo "${svc}_digest=$digest" >> "$GITHUB_OUTPUT"
done
