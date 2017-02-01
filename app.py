#!/usr/bin/env python

from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
import urllib.request, urllib.parse, urllib.error
import json
import os
import datetime

from flask import Flask
from flask import request
from flask import make_response

# Flask app should start in global layout
app = Flask(__name__)


@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    res = processEventsRequest(req)
    print("Total Response1: " + res)
    res = json.dumps(res, indent=4)
    print("Total Response2: " + res)

    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


def processEventsRequest(req):
    action = req.get("result").get("action")
    if not action.startswith("event"):
        return {}
    baseurl = "https://dfmobile-tzorg.cs12.force.com/customers/services/apexrest/events?"
    eventname = getEventName(req)
    if eventname is None:
        return {}
    url = baseurl + urllib.parse.urlencode({'names': eventname})
    
    result = urllib.request.urlopen(url).read()
    data = json.loads(result)
    
    res = routeAndRespond(action, data)
    return res

def routeAndRespond(action, data):
    if action == "event.location":
        return getEventVenue(data)
    elif action == "event.time":
        return getEventTime(data)
    return {}    
        
def getEventName(req):
    result = req.get("result")
    parameters = result.get("parameters")
    eventname = parameters.get("event-name")
    if eventname is None:
        return None

    return eventname


def getEventVenue(data):
    event = data[0]
    if event is None:
        return {}
    
    name = event.get('Label__c')
    venue = event.get('Venue__r')
    if venue is None:
        return {}
    
    city = venue.get('City__c')
    country = venue.get('Country__c')
    state = venue.get('State__c')
    latlong = venue.get('Lat_Long__c')
    
    if (city is None) or (country is None) or (state is None):
        return {}
    
    speech = "The venue for the event " + name + " is " + city + ", " + state + ", " + country

    print("Response:")
    print(speech)


    facebook_message = {
        "attachment": {
            "type": "template",
            "payload": {
                "template_type": "generic",
                "elements": [
                    {
                        "title": name,
                        #"image_url": "https://appexchange--c.na45.content.force.com/servlet/servlet.ImageServer?id=0153A000002pWmm&oid=00D300000000iTz&lastMod=1472819734000",
                        "subtitle": city + ", " + state,
                        "buttons": [
                            {
                                "type": "web_url",
                                "url": "https://www.google.com/maps?q="+latlong.get('latitude')+","+latlong.get('longitude'),
                                "title": "Open in Maps"
                            }
                        ]
                    }
                ]
            }
        }
    }

    return {
        "speech": speech,
        "displayText": speech,
        "data": {"facebook": facebook_message},
        # "contextOut": [],
        "source": "apiai-events"
    }

def getEventTime(data):
    event = data[0]
    if event is None:
        return {}
        
    name = event.get('Label__c')
    
    starttime = datetime.datetime.strptime(event.get('Event_Start_Date__c'), '%Y-%m-%dT%H:%M:%S.%f+0000').strftime('%c')
    endtime = datetime.datetime.strptime(event.get('Event_End_Date__c'), '%Y-%m-%dT%H:%M:%S.%f+0000').strftime('%c')

    print(starttime)
    
    if (starttime is None):
        return {}
    
    speech = name + " starts from " + starttime
    
    if (endtime is not None):
        speech = speech + " and ends at " + endtime

    print("Response:")
    print(speech)

    return {
        "speech": speech,
        "displayText": speech,
        # "data": data,
        # "contextOut": [],
        "source": "apiai-events"
    }



if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=False, port=port, host='0.0.0.0')
