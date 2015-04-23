#!/usr/bin/python

import sys
import os
import urllib
import json
import requests
import dateutil.parser
import datetime
from requests_oauthlib import OAuth2Session

#Runkeeper client ID
client_id = ''

#This script doesn't do any authentication w/ Garmin, so be sure your activities are set to public.
gc_userid = ''

#Runkeeper token - get this by running the getrktoken.py script
rk_token = ''

#When two consecutive GPS points are this many seconds apart (or more), consider it to be a pause.
#My Garmin 620 seems to record every 9 seconds, so 20 seconds seemed to be a safe estimate for me.
pause_threshold = 20

#Create an authenticated Runkeeper session.
my_token={'token_type': 'Bearer', 'access_token': rk_token}
rk = OAuth2Session(client_id,token=my_token)

def get_rk_most_recent_date():
	r = rk.get('https://api.runkeeper.com/fitnessActivities')
	rkdts = r.json()['items'][0]['start_time']
	rkd = (dateutil.parser.parse(rkdts))
	if 'utc_offset' in r.json()['items'][0]:
		rkutc_offset = r.json()['items'][0]['utc_offset']
		rkd_utc = (rkd - datetime.timedelta(hours=rkutc_offset))
		return rkd_utc
	else:
		return rkd

def get_new_gc_activities(rk_date):
	start=1
	limit=3
	id_list=[]
	while True:
		gc_activities_url = 'https://connect.garmin.com/proxy/activitylist-service/activities/' + gc_userid + '?start=' + str(start) + '&limit=' + str(limit)
		r = requests.get(gc_activities_url)
		act_list = r.json()['activityList']
		if act_list:
			for activity in act_list:
				gc_date = dateutil.parser.parse(activity['startTimeGMT'])
				if gc_date >= rk_date:
					id_list.append((activity['activityId']))
				else:
					break
		else:
			break
		start+=limit
	return id_list

def build_rk_record(gc_activity_id):
	gc_activity_summary_url = 'https://connect.garmin.com/modern/proxy/activity-service-1.3/json/activity/' + str(gc_activity_id)
	r = requests.get(gc_activity_summary_url)
	act_summary = r.json()['activity']
	type = act_summary['activityType']['display']
	start = act_summary['activitySummary']['BeginTimestamp']['display']
	start_dt = datetime.datetime.strptime(start, '%a, %d %b %Y %H:%M')
	start_string = datetime.datetime.strftime(start_dt, '%a, %d %b %Y %H:%M:00')
	duration = act_summary['activitySummary']['SumMovingDuration']['value']
	
	#This section gets the data points from Garmin.  The problem is, Garmin puts them in a different sequence each time!
	#So you have to find the key for the data elements that are needed.
	#Also, depending on the user agent, Garmin sends either 10 or 13 data points.  So the user agent has to be faked here.
	gc_activity_details_url = 'https://connect.garmin.com/modern/proxy/activity-service-1.3/json/activityDetails/' + str(gc_activity_id)
	header = {'user-agent':'curl'}
	r = requests.get(gc_activity_details_url,headers=header)
	act_measurements = r.json()['com.garmin.activity.details.json.ActivityDetails']['measurements']
	for measurement in act_measurements:
		if measurement['key'] == 'sumElapsedDuration':
			duration_index = measurement['metricsIndex']
		elif measurement['key'] == 'directLongitude':
                        longitude_index = measurement['metricsIndex']
		elif measurement['key'] == 'directLatitude':
                        latitude_index = measurement['metricsIndex']
		elif measurement['key'] == 'directElevation':
			elevation_index = measurement['metricsIndex']
	act_metrics = r.json()['com.garmin.activity.details.json.ActivityDetails']['metrics']
	
	path = []
	for metrics in act_metrics:
		path_point = {}
		path_point['timestamp'] = metrics['metrics'][duration_index]
		path_point['latitude'] = metrics['metrics'][latitude_index]
		path_point['longitude'] = metrics['metrics'][longitude_index]
		path_point['altitude'] = metrics['metrics'][elevation_index] 
		path_point['type'] = 'gps'
		path.append(path_point)
	
	#Change the type for the first and last GPS points 
	path[0]['type'] = 'start'
	path[len(path)-1]['type'] = 'end'

	#Now use the pause threshold value set above to determine where to place the pauses
	for i in range(len(path)):
		if path[i]['type'] == 'gps':
			if (path[i+1]['timestamp'] - path[i]['timestamp']) > pause_threshold:
				path[i]['type'] = 'pause'
				path[i+1]['type'] = 'resume'	
	
	rk_record = {}
	rk_record['type'] = type
	rk_record['start_time'] = start_string
	rk_record['duration'] = duration
	rk_record['path'] = path
	
	return(rk_record)


def rk_upload(rk_upload_data, gc_activity_id):
	headers = {'Content-Type':'application/vnd.com.runkeeper.NewFitnessActivity+json'}
	r = rk.post('https://api.runkeeper.com/fitnessActivities', headers=headers, data=json.dumps(rk_upload_data))
	if r.status_code != 202:
		print ("Error uploading Garmin activity ", gc_activity_id)

def main():

	#If any parameters have been passed, they should be Garmin activity IDs.
	#If there are no parameters passed, the pull in everything on Garmin that is newer than the newest activity on Runkeeper.
	if len(sys.argv) > 1 :
		gc_activity_ids = sys.argv
		gc_activity_ids.pop(0)
	else:
		rk_date = get_rk_most_recent_date()
		gc_activity_ids = get_new_gc_activities(rk_date)

	for id in gc_activity_ids:
		rk_upload_data = build_rk_record(id)
		rk_upload(rk_upload_data, id)

if __name__ == "__main__": main()

