#!/bin/sh
#Copyright (C) BlueWave Projects and Services 2015-2023
#This software is released under the GNU GPL license.
#and mod by siddiq sanjaya bakti
#

status=$1
clientip=$2
b64query=$3

do_ndsctl () {
	local timeout=4

	for tic in $(seq $timeout); do
		ndsstatus="ready"
		ndsctlout=$(eval ndsctl "$ndsctlcmd")

		for keyword in $ndsctlout; do

			if [ $keyword = "locked" ]; then
				ndsstatus="busy"
				sleep 1
				break
			fi
		done

		if [ "$ndsstatus" = "ready" ]; then
			break
		fi
	done
}

get_client_zone () {
	failcheck=$(echo "$clientif" | grep "get_client_interface")

	if [ -z $failcheck ]; then
		client_if=$(echo "$clientif" | awk '{printf $1}')
		client_meshnode=$(echo "$clientif" | awk '{printf $2}' | awk -F ':' '{print $1$2$3$4$5$6}')
		local_mesh_if=$(echo "$clientif" | awk '{printf $3}')

		if [ ! -z "$client_meshnode" ]; then
			client_zone="MeshZone: $client_meshnode"
		else
			client_zone="LocalZone: $client_if"
		fi
	else
		client_zone=""
	fi
}

htmlentityencode() {
	entitylist="
		s/\"/\&quot;/g
		s/>/\&gt;/g
		s/</\&lt;/g
		s/%/\&#37;/g
		s/'/\&#39;/g
		s/\`/\&#96;/g
	"
	local buffer="$1"

	for entity in $entitylist; do
		entityencoded=$(echo "$buffer" | sed "$entity")
		buffer=$entityencoded
	done

	entityencoded=$(echo "$buffer" | awk '{ gsub(/\$/, "\\&#36;"); print }')
}

parse_parameters() {

	if [ "$status" = "status" ]; then
		ndsctlcmd="json $clientip"
		do_ndsctl

		if [ "$ndsstatus" = "ready" ]; then
			param_str=$ndsctlout

			for param in gatewayname gatewayaddress gatewayfqdn mac version ip client_type clientif session_start session_end \
				last_active token state upload_rate_limit_threshold download_rate_limit_threshold \
				upload_packet_rate upload_bucket_size download_packet_rate download_bucket_size \
				upload_quota download_quota upload_this_session download_this_session upload_session_avg download_session_avg
			do
				val=$(echo "$param_str" | grep "\"$param\":" | awk -F'"' '{printf "%s", $4}')

				if [ "$val" = "null" ]; then
					val="Unlimited"
				fi

				if [ -z "$val" ]; then
					eval $param=$(echo "Unavailable")
				else
					eval $param=$(echo "\"$val\"")
				fi
			done

			# url decode and html entity encode gatewayname
			gatewayname_dec=$(printf "${gatewayname//%/\\x}")
			htmlentityencode "$gatewayname_dec"
			gatewaynamehtml=$entityencoded
			gatewaynamecut=$(echo "$gatewaynamehtml" | awk -F 'Node:' '{print $1}')
			# Get client_zone from clientif
			get_client_zone

			# Get human readable times:
			sessionstart=$(date -d "@$session_start" "+%Y-%m-%d %H:%M")

			if [ "$session_end" = "Unlimited" ]; then
				sessionend=$session_end
			else
				sessionend=$(date -d "@$session_end" "+%Y-%m-%d %H:%M")
			fi

			lastactive=$(date -d "@$last_active" "+%Y-%m-%d %H:%M")
		fi
	else
		mountpoint=$(/usr/lib/opennds/libopennds.sh tmpfs)
		. $mountpoint/ndscids/ndsinfo
	fi
}
header() {
    echo '<!DOCTYPE html>
	<html lang="en">

	<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>Hotspot Manager</title>
	<link href="/cover.jpg" rel="icon">
	<style media="screen">
		* {
		padding: 0;
		margin: 0;
		box-sizing: border-box;
		}

		body {
		display: flex;
		justify-content: center;
		align-items: center;
		height: 100vh;
		margin: 0;

		font-family: 'Poppins', sans-serif;
		background-color: #000000;
		}

		#loading-container {
		display: flex;
		align-items: center;
		justify-content: center;
		position: fixed;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		background-color: #fdfdfd;
		z-index: 1000;
		}

		#loading-logo {
		width: 80px;
		animation: heartbeat 1.5s infinite;
		transition: opacity 0.5s ease-in-out;
		}

		@keyframes heartbeat {
		0% {
			transform: scale(1);
		}

		25% {
			transform: scale(1.1);
		}

		50% {
			transform: scale(1);
		}

		75% {
			transform: scale(1.1);
		}

		100% {
			transform: scale(1);
		}
		}

		video {
		position: fixed;
		top: 50%;
		left: 50%;
		min-width: 100%;
		min-height: 100%;
		width: auto;
		height: auto;
		z-index: -1;
		transform: translateX(-50%) translateY(-50%);
		}

		.background {
		width: 100%;
		height: 100vh;
		position: absolute;
		top: 0;
		left: 0;
		overflow: hidden;
		
		z-index: -1;
		}

		.background .shape {
		height: 200px;
		width: 200px;
		position: absolute;
		border-radius: 100%;
		}

		.shape:first-child {
		background: linear-gradient(
			#1845ad,
			#23a2f6
		);
		left: -80px;
		top: -80px;
		}

		.shape:last-child {
		background: linear-gradient(
			to right,
			#ff512f,
			#f09819
		);
		right: -30px;
		bottom: -30px;
		}

		form {
		background-color: rgba(255, 255, 255, 0.13);
		border-radius: 10px;
		backdrop-filter: blur(10px);
		border: 2px solid rgba(255, 255, 255, 0.1);
		box-shadow: 0 0 40px rgba(8, 7, 16, 0.6);
		padding: 20px;
		width: 100%;
		max-width: 400px;
		text-align: center;
		position: relative;
		animation: fadeIn 1s ease-out;
		visibility: hidden;
		opacity: 0;
		margin-top: -15%;
		}

		#login-form {
		visibility: hidden;
		opacity: 0;
		transition: opacity 0.5s ease-in-out;
		}

		form h3 {
		font-size: 24px;
		font-weight: 500;
		line-height: 32px;
		margin-bottom: 10px;
		color: #ffffff;
		}

		form p {
		font-size: 14px;
		color: #ffffff;
		margin-bottom: 20px;
		}

		label {
		display: block;
		margin-top: 20px;
		font-size: 16px;
		font-weight: 500;
		color: #ffffff;
		text-align: left;
		}

		input {
		display: block;
		height: 40px;
		width: 100%;
		background-color: rgba(255, 255, 255, 0.07);
		border-radius: 3px;
		padding: 0 10px;
		margin-top: 8px;
		font-size: 14px;
		font-weight: 300;
		color: #ffffff;
		border: none;
		outline: none;
		}

		::placeholder {
		color: #e5e5e5;
		}

		button {
		margin-top: 20px;
		width: 100%;
		background-color: #ffffff;
		color: #080710;
		padding: 15px 0;
		font-size: 18px;
		font-weight: 600;
		border-radius: 5px;
		cursor: pointer;
		border: none;
		outline: none;
		}

		.alert {
		font-size: 14px;
		color: #ffffff;
		margin-top: 10px;
		background-color: #ffcc00;
		padding: 10px;
		color: #080710;
		border-radius: 5px;
		}

		@keyframes fadeIn {
		from {
			visibility: visible;
			opacity: 0;
		}
		to {
			opacity: 1;
		}
		}
	</style>
	</head>
	'
}

footer(){
    echo "  <script>
		setTimeout(function () {
		const loadingContainer = document.getElementById('loading-container');
		const loadingLogo = document.getElementById('loading-logo');
		const loginForm = document.getElementById('login-form');

		loadingLogo.style.opacity = '0';

		setTimeout(function () {
			loadingContainer.style.display = 'none';
			loginForm.style.visibility = 'visible';
			loginForm.style.opacity = '1';
		}, 500);
		}, 1000);

	</script>
	</body>

	</html>"
}
body() {

    if [ "$status" = "err511" ]; then

		echo "<head>
        <meta http-equiv='refresh' content='0; url=\"$url/login\"' />
        </head>
		"

    elif [ "$status" = "status" ]; then
			pagebody='
			<body>
			<div id="loading-container">
				<img id="loading-logo" src="/cover.jpg" alt="Loading">
			</div>
			<video autoplay muted loop>
				<source src="/static/video/login_vid.mp4" type="video/mp4">
				Your browser does not support the video tag.
			</video>
			<div class="background">
				<div class="shape"></div>
				<div class="shape"></div>
			</div>
			<form id="login-form"  style="visibility: hidden; opacity: 0;"  action="/opennds_deny/" method="GET">
				<h3>'${gatewaynamecut}'</h3>
            	<label for="ipAddress">IP / Mac Address</label>
					<input type="text" id="ipAddress" value="'${ip}' / '${mac}'" readonly>

				<label for="sessionStart to end">Session Start to End</label>
					<input type="text" value="'${sessionstart}' to '${sessionend}'" readonly>

				<label for="downloadRateLimit">Download / Upload Rate Limit</label>
					<input type="text" id="downloadRateLimit" value="'${download_rate_limit_threshold}' / '${upload_rate_limit_threshold}'" readonly>

				<label for="downloadPacketRate">Download / Upload Packet Rate</label>
					<input type="text" id="downloadPacketRate" value="'${download_packet_rate}' / '${upload_packet_rate}'" readonly>

				<label for="downloadQuota">Download / Upload Quota</label>
					<input type="text" id="downloadQuota" value="'${download_quota}' / '${upload_quota}'" readonly>

				<label for="downloadAvgNow">Download / Upload Average Now</label>
					<input type="text" id="downloadAvgNow" value="'${download_session_avg}' / '${upload_session_avg}'" readonly>
				<button>Log Out</button>
				</form>
			'
        
        echo "$pagebody"
        
	elif [ "$ndsstatus" = "busy" ]; then
		pagebody="
			<hr>
			<b>The Portal is busy, please click or tap \"Refresh\"<br><br></b>
			<form>
				<input type=\"button\" VALUE=\"Refresh\" onClick=\"history.go(0);return true;\">
			</form>
		"
        echo "$pagebody"
	else
		exit 1
	fi

	
}

# Start generating the html:
if [ -z "$clientip" ]; then
	exit 1
fi

if [ "$status" = "status" ] || [ "$status" = "err511" ]; then
	parse_parameters

	if [ -z "$gatewayfqdn" ] || [ "$gatewayfqdn" = "disable" ] || [ "$gatewayfqdn" = "disabled" ]; then
		url="http://$gatewayaddress"
	else
		url="http://$gatewayfqdn"
	fi

	header
	body
	footer
	exit 0
else
	exit 1
fi
