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
	<meta charset="utf-8">
	<meta content="width=device-width, initial-scale=1.0" name="viewport">

	<title>Hotspot Manager</title>
	<meta content="" name="description">
	<meta content="" name="keywords">

	<!-- Favicons -->
	<link href="/cover.jpg" rel="icon">
	<!-- Google Fonts -->

	<!-- Vendor CSS Files -->
	<link href="/bootstrap.css" rel="stylesheet">
	<link rel="stylesheet" type="text/css" href="/style.css">

	</head>'
}
footer(){
    echo '<a href="#" class="back-to-top d-flex align-items-center justify-content-center"><i class="bi bi-arrow-up-short"></i></a>

		<script src="/bootstrap.bundle.min.js"></script>
		<script src="/main.js"></script>

		</body>

	</html>'
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
                <main>
                    <div class="container">

                    <section class="section register min-vh-50 d-flex flex-column align-items-center justify-content-center">
                        <div class="container">
                        <div class="row justify-content-center">
                            <div class="col col d-flex flex-column align-items-center justify-content-center">

                            <div class="d-flex justify-content-center py-4">
                                <a class="logo d-flex align-items-center w-auto">
                                <img src="/cover.jpg" alt="">
                                <span class="d-none d-lg-block">HotSpot</span>
                                </a>
                            </div><!-- End Logo -->

                            <div class="card w-200 mb-3">

                                <div class="card-body">

                                    <div class="pt-1 pb-2">
                                        <h5 class="card-title text-center pb-0 fs-4">Status</h5>
                                        <p class="text-center small">Status You Network</p>
                                    </div>

                                    <form action="/opennds_deny/" method="GET">
                                    <div class="row g-3">
										<ul class="list-group">
											<li class="list-group-item">IP Address: '$ip'</li>
											<li class="list-group-item">MAC Address: '$mac'</li>
											<li class="list-group-item">Session Start: '$sessionstart'</li>
											<li class="list-group-item">Session End: '$sessionend'</li>
											<li class="list-group-item">Download Rate Limit: '$download_rate_limit_threshold'</li>
											<li class="list-group-item">Download Packet Rate: '$download_packet_rate'</li>
											<li class="list-group-item">Download Qouta: '$download_quota'</li>
											<li class="list-group-item">Download Average Now: '$download_session_avg'</li>
											<li class="list-group-item">Upload Rate Limit: '$upload_rate_limit_threshold'</li>
											<li class="list-group-item">Upload Packet Rate: '$upload_packet_rate'</li>
											<li class="list-group-item">Upload Qouta: '$upload_quota'</li>
											<li class="list-group-item">Upload Average Now: '$upload_session_avg'</li>
										</ul>

                                        <div class="col-12">
                                            <button class="btn btn-primary w-100" type="submit">Log Out</button>
                                        </div>
                                        
                                    </div>
                                    
                                </form>
                                </div>
                            </div>

                            </div>
                        </div>
                        </div>

                    </section>

                    </div>
                </main>
				
			"'
        
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
