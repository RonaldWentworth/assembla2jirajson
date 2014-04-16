#!/usr/bin/env python
# -*- coding: utf-8 -*-

#import a2j_config
import sys
import json
import re

data_input = []
data_output = []

if len(sys.argv)<3 or len(sys.argv)>4:
	print "Error incorrect argument number"
	print "Usage: "+sys.argv[0]+"<source_file> <destination_file> (Optionnal |<attachement_url>)"
	exit()

file_input = sys.argv[1]
file_output = sys.argv[2]

if len(sys.argv)==4:
	attachement_url = sys.argv[3]
else:
	attachement_url = ""

#load config file
config = json.loads(open('config.json').read())
link_conversion = config["link_conversion"]
workflow_conversion = config["workflow_conversion"]
user_conversion = config["user_conversion"]

input_field = [
	'user_roles, ',
	'spaces, ',
	'milestones, ',
	'ticket_statuses, ',
	'tickets, ',
	'estimate_histories, ',
	'user_tasks, ',
	'ticket_comments, ',
	'ticket_associations, ',
	'documents, ',
	'document_versions, ' ]

input_dict = {}

#Assembla export file is not a regular json first we serialize data we want to use

#Initiate a dict key for each input type we want to save
for s in input_field:
	input_dict[s] = ''

#read input file and save wanted line into destination key
with open(file_input) as f:
	for line in f:
		for s in input_field:
			if line.startswith(s):
				if input_dict[s]!='':
					input_dict[s] += ','+line[len(s):-1]
				else:
					input_dict[s] += line[len(s):-1]

#Convert saved line into standard json data
for s in input_field:
	data_input.append(json.loads('{"'+s[:-2]+'": ['+input_dict[s]+']}'))

#Now we can convert JSON data according to JIRA JSON schema

# Some function to return JIRA association and convert value between Assembla and Jira

def reporter_login(id,user_dict):
	login=""
	for element in user_dict:
		if element["id"] == id:
			login=element["login"]
	return login

def ticket_milestone(id,input_dict):
	did=0
	dtitle=2
	milestone=""
	for element in input_dict[2]["milestones"]:
		if element[did] == id:
			milestone=element[title]
	return milestone

def space_key (id):
	key=""
	did=0
	name=1
	for element in data_input[1]["spaces"]:
		if element[did] == id:
			key=element[name]
	return key

def ticket_key (id):
	key=""
	did=0
	space_id=4
	number=1
	for element in data_input[4]["tickets"]:
		if element[did] == id:
			key=space_key(element[space_id])+'-'+str(element[number])
	return key

# we use "workflow_conversion" parameter for mapping assembla workflow to jira workflow
# if a status is not present in "workflow_conversion" we use internal assembla state
def ticket_status(id,input_dict):
	dname=2
	did=0
	state=3
	jira_name=""
	for element in input_dict[3]["ticket_statuses"]:
		print element[dname]
		if element[did] == id:
			if element[dname] in workflow_conversion:
				jira_name = workflow_conversion[element[dname]]
			else:
				if element[state] == 1:
					jira_name = "Open"
				else:
					jira_name = "Closed"
	return jira_name

def ticket_priority(id):
	ticket_priorities={1:"Blocker",2:"Critical",3:"Major",4:"Minor",5:"Trivial"}
	return ticket_priorities[id]

#def convert_links(data):
#	new_data=re.sub(r'(.*)\[\[file\:(.*)\]\](.*)', r'\1[http://localhost:8080/jira/\2]\3',data)
#	return new_data
#Convert input string according to JSON encoding

users_output = ''

for i, element in enumerate(user_conversion):
	users_output += '{"name":'+json.dumps(element["login"])+','
	if "email" in element:
		users_output += '"email":'+json.dumps(element["email"])+','
	users_output += '"fullname": '+json.dumps(element["fullname"])+'}'
	if i < len(user_conversion)-1:
		users_output += ','


links_output = ''
relationship=3
ticket1_id=1
ticket2_id=2
for i, element in enumerate(data_input[8]["ticket_associations"]):
	links_output += '{"name":'+json.dumps(link_conversion[str(element[relationship])])+','
	links_output += '"sourceId":'+json.dumps(ticket_key(element[ticket1_id]))+','
	links_output += '"destinationId":'+json.dumps(ticket_key(element[ticket2_id]))+'}'
	if i < len(data_input[8]["ticket_associations"])-1:
		links_output += ','


versions_output = {}
dspace_id=6
is_completed=8
due_date=1
title=2
for element in data_input[2]["milestones"]:
	space_id=element[dspace_id]
	if element[is_completed]==1:
		released='true'
	else:
		released='false'
	if element[due_date] is None:
		releaseDate=''
	else:
		releaseDate=str(element[due_date])+'T00:00:00+00:00'
	if space_id not in versions_output:
		versions_output[space_id] = '{"name":'+json.dumps(element[title])+','
		versions_output[space_id] += '"released":'+released+','
		versions_output[space_id] += '"releaseDate":"'+releaseDate+'"}'
	else:
		versions_output[space_id] += ',{"name":'+json.dumps(element[title])+','
		versions_output[space_id] += '"released":'+released+','
		versions_output[space_id] += '"releaseDate":"'+releaseDate+'"}'

comments_output = {}
dticket_id=1
comment=5
user_id=2
created_on=3
for element in data_input[7]["ticket_comments"]:
	ticket_id=element[dticket_id]
	# we do not import empty comment created by assembla to notify user actions
	if (element[comment] is not None) and ((element[comment] != "")):
		if ticket_id not in comments_output:
			comments_output[ticket_id] = ''
		else:
			comments_output[ticket_id] += ','
		comments_output[ticket_id] += '{"author":'+json.dumps(reporter_login(element[user_id],user_conversion))+','
		comments_output[ticket_id] += '"body":'+json.dumps(element[comment])+','
		comments_output[ticket_id] += '"created":"'+element[created_on]+'"}'


attachments_version_output = {}
ddocument_id=1
version=2
for element in data_input[10]["document_versions"]:
	document_id=element[ddocument_id]
	if document_id not in attachments_version_output:
		attachments_version_output[document_id] = []
	attachments_version_output[document_id].append(element[version])

attachments_output = {}
dticket_id=18
did=0
name=2
created_at=5
created_by=7
description=3
for element in data_input[9]["documents"]:
	ticket_id=element[dticket_id]
	document_id=element[did]
	version_list=attachments_version_output[document_id]
	for version in version_list:
		if ticket_id not in attachments_output:
			attachments_output[ticket_id] = ''
		else:
			attachments_output[ticket_id] += ','
		if element[name] in attachments_output[ticket_id]:
			split_name= element[name].split(".")
			new_name = ".".join(split_name[0:-1])
			new_name += element[created_at].replace('-', '').replace('T', '').replace(':', '')[0:14]
			new_name += "."+".".join(split_name[-1:])
			attachments_output[ticket_id] += '{"name" :'+json.dumps(new_name)+','
		else:
			attachments_output[ticket_id] += '{"name" :'+json.dumps(element[name])+','
		attachments_output[ticket_id] += '"attacher":'+json.dumps(reporter_login(element[created_by],user_conversion))+','
		attachments_output[ticket_id] += '"created":'+json.dumps(element[created_at])+','
		if element[description] is not None:
			attachments_output[ticket_id] += '"description":'+json.dumps(element[description])+','
		attachments_output[ticket_id] += '"uri":"'+attachement_url+element[did]+'_'+str(version)+'"}'

issues_output = {}
dspace_id=4
summary=5
description=7
ticket_status_id=19
reporter_id=2
assigned_to_id=3
created_on=8
milestone_id=10
updated_at=9
completed_date=13
did=0
priority=6
dnumber=1

for element in data_input[4]["tickets"]:
	space_id=element[dspace_id]
	if space_id not in issues_output:
		issues_output[space_id] = ''
	else:
		issues_output[space_id] += ','
	issues_output[space_id] += '{"summary":'+json.dumps(element[summary])+','
	issues_output[space_id] += '"description":'+json.dumps(element[description])+','
	issues_output[space_id] += '"status":'+json.dumps(ticket_status(element[ticket_status_id],data_input))+','
	issues_output[space_id] += '"reporter":'+json.dumps(reporter_login(element[reporter_id],user_conversion))+','
	issues_output[space_id] += '"assignee":'+json.dumps(reporter_login(element[assigned_to_id],user_conversion))+','
	issues_output[space_id] += '"created":"'+element[created_on]+'",'
	if element[milestone_id] is not None:
		issues_output[space_id] += '"fixedVersions":['+json.dumps(ticket_milestone(element[milestone_id],data_input))+'],'
	if element[updated_at] is not None:
		issues_output[space_id] += '"updated":"'+element[updated_at]+'",'
	if element[completed_date] is not None:
		issues_output[space_id] += '"resolution":"Resolved",'
		issues_output[space_id] += '"resolutionDate":"'+element[completed_date]+'",'
	if element[did] in comments_output:
		issues_output[space_id] += '"comments":['+comments_output[element[did]]+'],'
	if element[priority] is not None:
		issues_output[space_id] += '"priority":'+json.dumps(ticket_priority(element[priority]))+','
	if element[did] in attachments_output:
		issues_output[space_id] += '"attachments":['+attachments_output[element[did]]+'],'
	issues_output[space_id] += '"key":"'+space_key(space_id)+'-'+str(element[dnumber])+'",'
	issues_output[space_id] += '"externalId":"'+space_key(space_id)+'-'+str(element[dnumber])+'"}'

project_output = ''
dname=1
description=2
did=0
for i, element in enumerate(data_input[1]["spaces"]):
	project_output += '{"name":'+json.dumps(element[dname])+','
	project_output += '"key":"'+element[dname]+'",'
	if element[description] != "":
		project_output += '"description":'+json.dumps(element[description])+','
	if versions_output!={}:
		project_output += '"versions":['+versions_output[element[did]]+'],'
	project_output += '"issues":['+issues_output[element[did]]+']}'
	if i < len(data_input[1]["spaces"])-1:
		project_output += ','

#Create JSON data and write it to export file

data_output.append(json.loads('{"users": ['+users_output+'],"links": ['+links_output+'],"projects": ['+project_output+']}'))

with open(file_output, 'wb') as f:
	f.write((json.dumps(data_output))[1:-1])


