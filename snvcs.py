import requests
import logging
from requests.auth import HTTPBasicAuth
import re
from bs4 import BeautifulSoup as Soup
import time
from datetime import datetime
import getpass


#limit the number of scripts to be processed
response_limit = 2

#list of all sys id's retrieved
sys_ids_list = []

#target url
url = 'https://demo004.service-now.com/sys_script_include_list.do?SOAP'

#body of SOAP request
body = '''<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sys="http://www.service-now.com/sys_script_include">
   <soapenv:Header/>
   <soapenv:Body>
      <sys:getKeys>
         <active>true</active>
         <__limit>'''+ str(response_limit) +'''</__limit>
      </sys:getKeys>
   </soapenv:Body>
</soapenv:Envelope>'''

#login info
username = 'admin'
password = 'admin'
#password = getpass.getpass()

#logging information:
#level
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#output file for logging activity
handler = logging.FileHandler("Activity.log")
handler.setLevel(logging.INFO)

#format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.info("Start new session\n")

#connection details
authorization = HTTPBasicAuth(username, password)

proxyDictionary = {'http' : "http://127.0.0.1:8888", 'https' : "http://127.0.0.1:8888"}
 
headers = {"SOAPAction":"http://www.service-now.com/sys_script_include/getRecords"}

logger.info('Establishing connection for sys_id retrieval')

#SOAP raw response
connection = requests.post(url=url, data=body, auth=authorization) #, headers=headers, proxies=proxyDictionary, verify=False
logger.info("Connection status code: "+ str(connection.status_code) + "\n")
logger.debug("Connection: "+ str(connection))

if connection.status_code != 200:
    logger.info(connection.raise_for_status())

#parse the SOAP response with beautiful soup
results = Soup(connection.text)


#strip the html tags and split at ','
sys_ids_list = str(results.sys_id)[8:-9].split(',')
logger.info("* Retrieved " + str(len(sys_ids_list))+" sys ids *\n")



# - Functions - 

#sets the current time as the update time
def setUpdateTime():
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    write_file = open('last_updated_on.txt', "w")
    write_file.write(current_time)
    write_file.close()

#gets the date and time of last update
def getLastUpdateTime():
    try:
        input_file = open('last_updated_on.txt', 'r').read()
    except:
        input_file = "2000-01-01 00:00:00"
    return datetime.strptime(input_file, '%Y-%m-%d %H:%M:%S')

#gets the script corresponding to the sys_id
def get(sys_id):
    logger.info("Retrieving sys_id: "+ sys_id)
    body = '''<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sys="http://www.service-now.com/sys_script_include">
   <soapenv:Header/>
   <soapenv:Body>
      <sys:get>
         <sys_id>'''+sys_id+'''</sys_id>
      </sys:get>
   </soapenv:Body>
   </soapenv:Envelope>'''
    #SOAP raw response
    connection = requests.post(url=url, data=body, auth=authorization) #, headers=headers, proxies=proxyDict, verify=False
    logger.debug("Connection: "+ str(connection))
    if connection.status_code != 200:
        connection.raise_for_status()
    else:
        logger.info("Success")
    #parse the SOAP response with beautiful soup
    response = Soup(connection.text)
    return response


# creates a file with script's name, adds notes and the content of the script.
# If file exists, it will be overwritten
def process(script):
    logger.info("Processing "+ script.find('name').text)
    file_name = script.find('name').text + '.js'
    file = open(file_name, "w")
    file.write('//***************************** notes *******************************\n')
    file.write('//\n')
    file.write(str('// Name of script: ' + script.find('name').text + '\n'))
    file.write('// Description: ' + '\n')
    file.write('/* \n')
    file.write(str(script.description.text) + '\n')
    file.write('*/' + '\n')
    file.write('// System Info:' + '\n')
    file.write('//' + '\n')
    file.write(str('// sys_created_by: ' + script.sys_created_by.text + '\n'))
    file.write(str('// sys_created_on: ' + script.sys_created_on.text + '\n'))
    file.write(str('// sys_id:         ' + script.sys_id.text + '\n'))
    file.write(str('// sys_mod_count:  ' + str(script.sys_mod_count.text) + '\n'))
    file.write(str('// sys_updated_by: ' + script.sys_updated_by.text + '\n'))
    file.write(str('// sys_updated_on: ' + script.sys_updated_on.text + '\n'))
    file.write('//' + '\n')
    file.write('//************************ end of notes *******************************' + '\n')
    file.write('\n')
    file.write((script.script.text).encode('utf-8') + '\n')
    file.close()


# - main - 

#get the last time this script was executed
last_update_time = getLastUpdateTime()
logger.info("Last update time: "+ str(last_update_time) + "\n")

#retrieve each script by sys_id in a separate SOAP call
counter = 1
for sys_id in sys_ids_list:
    logger.info("Processing script: "+ str(counter))
    counter += 1
    
    #get the contents of the script with the current sys_id
    item = get(sys_id)
    
    #get the script's last update date
    item_update_date = datetime.strptime(item.sys_updated_on.text, '%Y-%m-%d %H:%M:%S')
    
    #if the script has been updated since the last_update_time, update the local file to reflect the changes
    if item_update_date > last_update_time:
        logger.info("Changes found. Updating: " + item.find('name').text + ".js\n")
        process(item)
    else:
        logger.info("No changes found since " + str(last_update_time) + "\n")

logger.info("Finished processing all sys ids.\n")

#set new update time
setUpdateTime()

logger.info(" * New update time set *\n")

logger.info("Exit\n\n\n")
