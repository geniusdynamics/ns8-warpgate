#!/bin/bash

#
# Copyright (C) 2023 Nethesis S.r.l.
# SPDX-License-Identifier: GPL-3.0-or-later
#

# Terminate on error
set -e

# Prepare variables for later use
images=()
# The image will be pushed to GitHub container registry
repobase="${REPOBASE:-ghcr.io/geniusdynamics}"
# Configure the image name
reponame="warpgate"
# Node.js 25+ no longer ships Corepack, install it from npm
# renovate: datasource=npm packageName=corepack
corepack_version=0.36.0
# Upstream Warpgate image, see https://github.com/warp-tech/warpgate/releases
# renovate: datasource=docker depName=ghcr.io/warp-tech/warpgate
warpgate_image="ghcr.io/warp-tech/warpgate:0.30.4"

# Create a new empty container image
container=$(buildah from scratch)

# Reuse existing nodebuilder-warpgate container, to speed up builds
if ! buildah containers --format "{{.ContainerName}}" | grep -q nodebuilder-warpgate; then
	echo "Pulling NodeJS runtime..."
	buildah from --name nodebuilder-warpgate -v "${PWD}:/usr/src:Z" docker.io/library/node:26.13.0-slim
	buildah run nodebuilder-warpgate sh -c "npm install -g corepack@${corepack_version} && corepack enable"
fi

echo "Build static UI files with node..."
buildah run \
	--workingdir=/usr/src/ui \
	--env="NODE_OPTIONS=--openssl-legacy-provider" \
	nodebuilder-warpgate \
	sh -c "yarn install && yarn build"

# Add imageroot directory to the container image
buildah add "${container}" imageroot /imageroot
buildah add "${container}" ui/dist /ui
# Setup the entrypoint, reserve three TCP ports (web UI, SSH, MySQL) and set a rootless container
buildah config --entrypoint=/ \
	--label="org.nethserver.authorizations=traefik@node:routeadm" \
	--label="org.nethserver.tcp-ports-demand=3" \
	--label="org.nethserver.rootfull=0" \
    --label="org.nethserver.min-core=3.0.0" \
	--label="org.nethserver.images=${warpgate_image}" \
	"${container}"
# Commit the image
buildah commit "${container}" "${repobase}/${reponame}"

# Append the image URL to the images array
images+=("${repobase}/${reponame}")

#
# NOTICE:
#
# It is possible to build and publish multiple images.
#
# 1. create another buildah container
# 2. add things to it and commit it
# 3. append the image url to the images array
#

#
# Setup CI when pushing to Github.
# Warning! docker::// protocol expects lowercase letters (,,)
if [[ -n "${CI}" ]]; then
	# Set output value for Github Actions
	printf "images=%s\n" "${images[*],,}" >>"${GITHUB_OUTPUT}"
else
	# Just print info for manual push
	printf "Publish the images with:\n\n"
	for image in "${images[@],,}"; do printf "  buildah push %s docker://%s:%s\n" "${image}" "${image}" "${IMAGETAG:-latest}"; done
	printf "\n"
fi
