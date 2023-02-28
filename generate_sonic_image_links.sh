#!/usr/bin/env bash
git checkout -b sonic_latest_images_links
git config --global user.email "sonicbld@microsoft.com"
git config --global user.name "mssonicbld"
git reset --hard
git pull origin sonic_latest_images_links

#set -euo pipefail


DEFID_BRCM_CMT="$(curl -s 'https://sonic-build.azurewebsites.net/ui/sonic/pipelines/138/builds?branchName=master' | jq -r '.value[0].id')"

DEFID_BRCM="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/definitions?name=Azure.sonic-buildimage.official.broadcom' | jq -r '.value[0].id')"
DEFID_MLNX="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/definitions?name=Azure.sonic-buildimage.official.mellanox' | jq -r '.value[0].id')"
DEFID_VS="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/definitions?name=Azure.sonic-buildimage.official.vs' | jq -r '.value[0].id')"
DEFID_INNO="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/definitions?name=Azure.sonic-buildimage.official.innovium' | jq -r '.value[0].id')"
DEFID_BFT="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/definitions?name=Azure.sonic-buildimage.official.barefoot' | jq -r '.value[0].id')"
DEFID_CHE="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/definitions?name=Azure.sonic-buildimage.official.cache' | jq -r '.value[0].id')"
DEFID_CTC="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/definitions?name=Azure.sonic-buildimage.official.centec' | jq -r '.value[0].id')"
DEFID_CTC64="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/definitions?name=Azure.sonic-buildimage.official.centec-arm64' | jq -r '.value[0].id')"
DEFID_GRC="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/definitions?name=Azure.sonic-buildimage.official.generic' | jq -r '.value[0].id')"
DEFID_MRV="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/definitions?name=Azure.sonic-buildimage.official.marvell-armhf' | jq -r '.value[0].id')"
DEFID_NPH="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/definitions?name=Azure.sonic-buildimage.official.nephos' | jq -r '.value[0].id')"

echo '{' > sonic_image_links.json
first=1
for BRANCH in  master 202111 202106 202012 201911 201811
do
	if [ -z "${first}" ]; then
		echo ',' >> sonic_image_links.json
	fi
	first=''
	BUILD_BRCM="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_BRCM}"'&branchName=refs/heads/'"${BRANCH}"'&$top=1&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].id')"
	BUILD_BRCM_TS="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_BRCM}"'?api-version=6.0' | jq -r '.queueTime')"
	BUILD_MLNX="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_MLNX}"'&branchName=refs/heads/'"${BRANCH}"'&$top=1&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].id')"
	BUILD_MLNX_TS="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_MLNX}"'?api-version=6.0' | jq -r '.queueTime')"
	BUILD_VS="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_VS}"'&branchName=refs/heads/'"${BRANCH}"'&$top=1&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].id')"
	BUILD_VS_TS="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_VS}"'?api-version=6.0' | jq -r '.queueTime')"
	BUILD_INNO="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_INNO}"'&branchName=refs/heads/'"${BRANCH}"'&$top=1&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].id')"
	BUILD_INNO_TS="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_INNO}"'?api-version=6.0' | jq -r '.queueTime')"
	BUILD_BFT="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_BFT}"'&branchName=refs/heads/'"${BRANCH}"'&$top=1&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].id')"
	BUILD_BFT_TS="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_BFT}"'?api-version=6.0' | jq -r '.queueTime')"
	BUILD_CHE="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_CHE}"'&branchName=refs/heads/'"${BRANCH}"'&$top=1&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].id')"
	BUILD_CHE_TS="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_CHE}"'?api-version=6.0' | jq -r '.queueTime')"
	BUILD_CTC="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_CTC}"'&branchName=refs/heads/'"${BRANCH}"'&$top=1&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].id')"
	BUILD_CTC_TS="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_CTC}"'?api-version=6.0' | jq -r '.queueTime')"
	BUILD_CTC64="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_CTC64}"'&branchName=refs/heads/'"${BRANCH}"'&$top=1&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].id')"
	BUILD_CTC64_TS="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_CTC64}"'?api-version=6.0' | jq -r '.queueTime')"
	BUILD_GRC="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_GRC}"'&branchName=refs/heads/'"${BRANCH}"'&$top=1&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].id')"
	BUILD_GRC_TS="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_GRC}"'?api-version=6.0' | jq -r '.queueTime')"
	BUILD_MRV="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_MRV}"'&branchName=refs/heads/'"${BRANCH}"'&$top=1&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].id')"
	BUILD_MRV_TS="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_MRV}"'?api-version=6.0' | jq -r '.queueTime')"
	BUILD_NPH="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_NPH}"'&branchName=refs/heads/'"${BRANCH}"'&$top=1&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].id')"
	BUILD_NPH_TS="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_NPH}"'?api-version=6.0' | jq -r '.queueTime')"

	#echo " [*] Last successful builds for \"${BRANCH}\":"
	#echo "     Broadcom: ${BUILD_BRCM}"
	#echo "     Mellanox: ${BUILD_MLNX}"
	#echo "     Virtual Switch: ${BUILD_VS}"

	ARTF_BRCM="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_BRCM}"'/artifacts?artifactName=sonic-buildimage.broadcom&api-version=5.1' | jq -r '.resource.downloadUrl')"
	ARTF_MLNX="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_MLNX}"'/artifacts?artifactName=sonic-buildimage.mellanox&api-version=5.1' | jq -r '.resource.downloadUrl')"
	ARTF_VS="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_VS}"'/artifacts?artifactName=sonic-buildimage.vs&api-version=5.1' | jq -r '.resource.downloadUrl')"
	ARTF_INNO="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_INNO}"'/artifacts?artifactName=sonic-buildimage.innovium&api-version=5.1' | jq -r '.resource.downloadUrl')"
	ARTF_BFT="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_BFT}"'/artifacts?artifactName=sonic-buildimage.barefoot&api-version=5.1' | jq -r '.resource.downloadUrl')"
	ARTF_CHE="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_CHE}"'/artifacts?artifactName=sonic-buildimage.cache&api-version=5.1' | jq -r '.resource.downloadUrl')"
	ARTF_CTC="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_CTC}"'/artifacts?artifactName=sonic-buildimage.centec&api-version=5.1' | jq -r '.resource.downloadUrl')"
	ARTF_CTC64="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_CTC64}"'/artifacts?artifactName=sonic-buildimage.centec-arm64&api-version=5.1' | jq -r '.resource.downloadUrl')"
	ARTF_GRC="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_GRC}"'/artifacts?artifactName=sonic-buildimage.generic&api-version=5.1' | jq -r '.resource.downloadUrl')"
	ARTF_MRV="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_MRV}"'/artifacts?artifactName=sonic-buildimage.marvell-armhf&api-version=5.1' | jq -r '.resource.downloadUrl')"
	ARTF_NPH="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds/'"${BUILD_NPH}"'/artifacts?artifactName=sonic-buildimage.nephos&api-version=5.1' | jq -r '.resource.downloadUrl')"

	COMMIT_BRCM_1="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_BRCM}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].sourceVersion')"
	COMMIT_BRCM_2="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_BRCM}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[1].sourceVersion')"
	COMMIT_MLNX_1="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_MLNX}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].sourceVersion')"
	COMMIT_MLNX_2="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_MLNX}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[1].sourceVersion')"
	COMMIT_VS_1="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_VS}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].sourceVersion')"
	COMMIT_VS_2="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_VS}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[1].sourceVersion')"
	COMMIT_INNO_1="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_INNO}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].sourceVersion')"
	COMMIT_INNO_2="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_INNO}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[1].sourceVersion')"
	COMMIT_BFT_1="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_BFT}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].sourceVersion')"
	COMMIT_BFT_2="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_BFT}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[1].sourceVersion')"
	COMMIT_CHE_1="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_CHE}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].sourceVersion')"
	COMMIT_CHE_2="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_CHE}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[1].sourceVersion')"
	COMMIT_CTC_1="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_CTC}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].sourceVersion')"
	COMMIT_CTC_2="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_CTC}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[1].sourceVersion')"
	COMMIT_CTC64_1="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_CTC64}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].sourceVersion')"
	COMMIT_CTC64_2="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_CTC64}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[1].sourceVersion')"
	COMMIT_GRC_1="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_GRC}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].sourceVersion')"
	COMMIT_GRC_2="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_GRC}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[1].sourceVersion')"
	COMMIT_MRV_1="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_MRV}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].sourceVersion')"
	COMMIT_MRV_2="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_MRV}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[1].sourceVersion')"
	COMMIT_NPH_1="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_NPH}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[0].sourceVersion')"
	COMMIT_NPH_2="$(curl -s 'https://dev.azure.com/mssonic/build/_apis/build/builds?definitions='"${DEFID_NPH}"'&branchName=refs/heads/'"${BRANCH}"'&$top=2&resultFilter=succeeded&api-version=6.0' | jq -r '.value[1].sourceVersion')"

	echo "\"${BRANCH}\": {" >> sonic_image_links.json
	echo "\"sonic-broadcom.bin\": {" >> sonic_image_links.json
	echo "  \"url\": \"$(echo "${ARTF_BRCM}" | sed 's/format=zip/format=file\&subpath=\/target\/sonic-broadcom.bin/')\","  >> sonic_image_links.json
	echo "  \"build-url\": \"https://dev.azure.com/mssonic/build/_build/results?buildId=${BUILD_BRCM}&view=results\"," >> sonic_image_links.json
	echo " \"diff\": \"https://github.com/sonic-net/sonic-buildimage/compare/"${COMMIT_BRCM_2}"..."${COMMIT_BRCM_1}"\"," >> sonic_image_links.json
	echo "  \"build\": \"${BUILD_BRCM}\"," >> sonic_image_links.json
	echo "  \"date\": \"${BUILD_BRCM_TS}\"" >> sonic_image_links.json
	echo " }," >> sonic_image_links.json
	echo "\"sonic-aboot-broadcom.swi\": {" >> sonic_image_links.json
	echo "  \"url\": \"$(echo "${ARTF_BRCM}" | sed 's/format=zip/format=file\&subpath=\/target\/sonic-aboot-broadcom.swi/')\"," >> sonic_image_links.json
	echo "  \"build-url\": \"https://dev.azure.com/mssonic/build/_build/results?buildId=${BUILD_BRCM}&view=results\"," >> sonic_image_links.json
	echo " \"diff\": \"https://github.com/sonic-net/sonic-buildimage/compare/"${COMMIT_BRCM_2}"..."${COMMIT_BRCM_1}"\"," >> sonic_image_links.json
	echo "  \"build\": \"${BUILD_BRCM}\"," >> sonic_image_links.json
	echo "  \"date\": \"${BUILD_BRCM_TS}\"" >> sonic_image_links.json
	echo " }," >> sonic_image_links.json
	echo "\"sonic-mellanox.bin\": {" >> sonic_image_links.json
	echo "  \"url\": \"$(echo "${ARTF_MLNX}" | sed 's/format=zip/format=file\&subpath=\/target\/sonic-mellanox.bin/')\"," >> sonic_image_links.json
	echo "  \"build-url\": \"https://dev.azure.com/mssonic/build/_build/results?buildId=${BUILD_MLNX}&view=results\"," >> sonic_image_links.json
	echo " \"diff\": \"https://github.com/sonic-net/sonic-buildimage/compare/"${COMMIT_MLNX_2}"..."${COMMIT_MLNX_1}"\"," >> sonic_image_links.json
	echo "  \"build\": \"${BUILD_MLNX}\"," >> sonic_image_links.json
	echo "  \"date\": \"${BUILD_MLNX_TS}\"" >> sonic_image_links.json
	echo " }," >> sonic_image_links.json
	echo "\"sonic-vs.img.gz\": {" >> sonic_image_links.json
	echo "  \"url\": \"$(echo "${ARTF_VS}" | sed 's/format=zip/format=file\&subpath=\/target\/sonic-vs.img.gz/')\"," >> sonic_image_links.json
	echo "  \"build-url\": \"https://dev.azure.com/mssonic/build/_build/results?buildId=${BUILD_VS}&view=results\"," >> sonic_image_links.json
	echo " \"diff\": \"https://github.com/sonic-net/sonic-buildimage/compare/"${COMMIT_VS_2}"..."${COMMIT_VS_1}"\"," >> sonic_image_links.json
	echo "  \"build\": \"${BUILD_VS}\"," >> sonic_image_links.json
	echo "  \"date\": \"${BUILD_VS_TS}\"" >> sonic_image_links.json
	echo " }," >> sonic_image_links.json
	echo "\"sonic-innovium.bin\": {" >> sonic_image_links.json
	echo "  \"url\": \"$(echo "${ARTF_INNO}" | sed 's/format=zip/format=file\&subpath=\/target\/sonic-innovium.bin/')\"," >> sonic_image_links.json
	echo "  \"build-url\": \"https://dev.azure.com/mssonic/build/_build/results?buildId=${BUILD_INNO}&view=results\"," >> sonic_image_links.json
	echo " \"diff\": \"https://github.com/sonic-net/sonic-buildimage/compare/"${COMMIT_INNO_2}"..."${COMMIT_INNO_1}"\"," >> sonic_image_links.json
	echo "  \"build\": \"${BUILD_INNO}\"," >> sonic_image_links.json
	echo "  \"date\": \"${BUILD_INNO_TS}\"" >> sonic_image_links.json
	echo " }," >> sonic_image_links.json
	echo "\"sonic-innovium-dbg.bin\": {" >> sonic_image_links.json
	echo "  \"url\": \"$(echo "${ARTF_INNO}" | sed 's/format=zip/format=file\&subpath=\/target\/sonic-innovium-dbg.bin/')\"," >> sonic_image_links.json
	echo "  \"build-url\": \"https://dev.azure.com/mssonic/build/_build/results?buildId=${BUILD_INNO}&view=results\"," >> sonic_image_links.json
	echo " \"diff\": \"https://github.com/sonic-net/sonic-buildimage/compare/"${COMMIT_INNO_2}"..."${COMMIT_INNO_1}"\"," >> sonic_image_links.json
	echo "  \"build\": \"${BUILD_INNO}\"," >> sonic_image_links.json
	echo "  \"date\": \"${BUILD_INNO_TS}\"" >> sonic_image_links.json	
	echo " }," >> sonic_image_links.json
	echo "\"sonic-barefoot.bin\": {" >> sonic_image_links.json
	echo "  \"url\": \"$(echo "${ARTF_BFT}" | sed 's/format=zip/format=file\&subpath=\/target\/sonic-barefoot.bin/')\"," >> sonic_image_links.json
	echo "  \"build-url\": \"https://dev.azure.com/mssonic/build/_build/results?buildId=${BUILD_BFT}&view=results\"," >> sonic_image_links.json
	echo " \"diff\": \"https://github.com/sonic-net/sonic-buildimage/compare/"${COMMIT_BFT_2}"..."${COMMIT_BFT_1}"\"," >> sonic_image_links.json
	echo "  \"build\": \"${BUILD_BFT}\"," >> sonic_image_links.json
	echo "  \"date\": \"${BUILD_BFT_TS}\"" >> sonic_image_links.json
	echo " }," >> sonic_image_links.json
	echo "\"sonic-centec.bin\": {" >> sonic_image_links.json
	echo "  \"url\": \"$(echo "${ARTF_CTC}" | sed 's/format=zip/format=file\&subpath=\/target\/sonic-centec.bin/')\"," >> sonic_image_links.json
	echo "  \"build-url\": \"https://dev.azure.com/mssonic/build/_build/results?buildId=${BUILD_CTC}&view=results\"," >> sonic_image_links.json
	echo " \"diff\": \"https://github.com/sonic-net/sonic-buildimage/compare/"${COMMIT_CTC_2}"..."${COMMIT_CTC_1}"\"," >> sonic_image_links.json
	echo "  \"build\": \"${BUILD_CTC}\"," >> sonic_image_links.json
	echo "  \"date\": \"${BUILD_CTC_TS}\"" >> sonic_image_links.json
	echo " }," >> sonic_image_links.json
	echo "\"sonic-centec-arm64.bin\": {" >> sonic_image_links.json
	echo "  \"url\": \"$(echo "${ARTF_CTC64}" | sed 's/format=zip/format=file\&subpath=\/target\/sonic-centec-arm64.bin/')\"," >> sonic_image_links.json
	echo "  \"build-url\": \"https://dev.azure.com/mssonic/build/_build/results?buildId=${BUILD_CTC64}&view=results\"," >> sonic_image_links.json
	echo " \"diff\": \"https://github.com/sonic-net/sonic-buildimage/compare/"${COMMIT_CTC64_2}"..."${COMMIT_CTC64_1}"\"," >> sonic_image_links.json
	echo "  \"build\": \"${BUILD_CTC64}\"," >> sonic_image_links.json
	echo "  \"date\": \"${BUILD_CTC64_TS}\"" >> sonic_image_links.json
	echo " }," >> sonic_image_links.json
	echo "\"sonic-generic.bin\": {" >> sonic_image_links.json
	echo "  \"url\": \"$(echo "${ARTF_GRC}" | sed 's/format=zip/format=file\&subpath=\/target\/sonic-generic.bin/')\"," >> sonic_image_links.json
	echo "  \"build-url\": \"https://dev.azure.com/mssonic/build/_build/results?buildId=${BUILD_GRC}&view=results\"," >> sonic_image_links.json
	echo " \"diff\": \"https://github.com/sonic-net/sonic-buildimage/compare/"${COMMIT_GRC_2}"..."${COMMIT_GRC_1}"\"," >> sonic_image_links.json
	echo "  \"build\": \"${BUILD_GRC}\"," >> sonic_image_links.json
	echo "  \"date\": \"${BUILD_GRC_TS}\"" >> sonic_image_links.json
	echo " }," >> sonic_image_links.json
	echo "\"sonic-generic-dbg.bin\": {" >> sonic_image_links.json
	echo "  \"url\": \"$(echo "${ARTF_GRC}" | sed 's/format=zip/format=file\&subpath=\/target\/sonic-generic-dbg.bin/')\"," >> sonic_image_links.json
	echo "  \"build-url\": \"https://dev.azure.com/mssonic/build/_build/results?buildId=${BUILD_GRC}&view=results\"," >> sonic_image_links.json
	echo " \"diff\": \"https://github.com/sonic-net/sonic-buildimage/compare/"${COMMIT_GRC_2}"..."${COMMIT_GRC_1}"\"," >> sonic_image_links.json
	echo "  \"build\": \"${BUILD_GRC}\"," >> sonic_image_links.json
	echo "  \"date\": \"${BUILD_GRC_TS}\"" >> sonic_image_links.json	
	echo " }," >> sonic_image_links.json
	echo "\"sonic-marvell-armhf.bin\": {" >> sonic_image_links.json
	echo "  \"url\": \"$(echo "${ARTF_MRV}" | sed 's/format=zip/format=file\&subpath=\/target\/sonic-marvell-armhf.bin/')\"," >> sonic_image_links.json
	echo "  \"build-url\": \"https://dev.azure.com/mssonic/build/_build/results?buildId=${BUILD_MRV}&view=results\"," >> sonic_image_links.json
	echo " \"diff\": \"https://github.com/sonic-net/sonic-buildimage/compare/"${COMMIT_MRV_2}"..."${COMMIT_MRV_1}"\"," >> sonic_image_links.json
	echo "  \"build\": \"${BUILD_MRV}\"," >> sonic_image_links.json
	echo "  \"date\": \"${BUILD_MRV_TS}\"" >> sonic_image_links.json
	echo " }," >> sonic_image_links.json
	echo "\"sonic-nephos.bin\": {" >> sonic_image_links.json
	echo "  \"url\": \"$(echo "${ARTF_NPH}" | sed 's/format=zip/format=file\&subpath=\/target\/sonic-nephos.bin/')\"," >> sonic_image_links.json
	echo "  \"build-url\": \"https://dev.azure.com/mssonic/build/_build/results?buildId=${BUILD_NPH}&view=results\"," >> sonic_image_links.json
	echo " \"diff\": \"https://github.com/sonic-net/sonic-buildimage/compare/"${COMMIT_NPH_2}"..."${COMMIT_NPH_1}"\"," >> sonic_image_links.json
	echo "  \"build\": \"${BUILD_NPH}\"," >> sonic_image_links.json
	echo "  \"date\": \"${BUILD_NPH_TS}\"" >> sonic_image_links.json
	echo " }" >> sonic_image_links.json
	echo -n "}" >> sonic_image_links.json
done
echo "\n}" >> sonic_image_links.json

git add sonic_image_links.json
git commit -m "latest links for sonic images in dedicated branch sonic_latest_images_links"
git push -f --set-upstream origin sonic_latest_images_links

