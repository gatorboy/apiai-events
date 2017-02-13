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
    #print("Total Response1: " + res)
    res = json.dumps(res, indent=4)
    #print("Total Response2: " + res)

    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


def processEventsRequest(req):
    action = req.get("result").get("action")
    if not action.startswith("event"):
        return {}
    baseurl = "https://dfmobile-tzorg.cs12.force.com/customers/services/apexrest/events?"
    flds = "Name,Id,Event_Start_Date__c,Event_End_Date__c,SponsorLevels__c,Label__c,Event_Time_Zone__c,Icon__c,Highlight_Color__c,Event_Type__c,ImageURL_Mobile__c,Venue__r.Name,Venue__r.Address__c,Venue__r.City__c,Venue__r.Country__c,Venue__r.State__c,Venue__r.Lat_Long__c,Phase__r.SessionsCanBeBooked__c,Phase__r.SessionsIncludeLogisticData__c,Phase__r.SessionsSurveyEnabled__c,Phase__r.MyAgendaVisible__c,Phase__r.SessionsVisible__c,Phase__r.RegistrationAvailable__c,ActiveSponsorCount__c,Pre_Event_Now_Card_Image__c,Post_Event_Now_Card_Image__c,Themes__c,JobFunctions__c,Industries__c,Products__c,Survey_Ad__c,MobileFeatures__c,Venue_Bookings__r,Session_Record_Type_Info__r.Display_Name__c,Session_Record_Type_Info__r.Session_Record_Type__c,Session_Record_Type_Info__r.Guests_Can_See_Sessions__c,Venue_Bookings__r.Venue__r.Name,Venue_Bookings__r.Venue__r.Address__c,Venue_Bookings__r.Venue__r.Address_2__c,Venue_Bookings__r.Venue__r.City__c,Venue_Bookings__r.Venue__r.State__c,Venue_Bookings__r.Venue__r.Country__c,Venue_Bookings__r.Venue__r.Postal_Code__c,Venue_Bookings__r.Venue__r.Postal_Code_Zip__c,Venue_Bookings__r.Venue__r.GoogleMapURL__c,Venue_Bookings__r.Venue__r.Lat_Long__Latitude__s,Venue_Bookings__r.Venue__r.Lat_Long__Longitude__s"
    eventname = getEventName(req)
    if eventname is None:
        return {}
    url = baseurl + urllib.parse.urlencode({'names': eventname, 'flds': flds})
    
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
    icon = event.get('Icon__c')
    venue = event.get('Venue__r')
    if venue is None:
        return {}
    
    venuename = venue.get('Name')
    address = venue.get('Address__c')
    city = venue.get('City__c')
    country = venue.get('Country__c')
    state = venue.get('State__c')
    latlong = venue.get('Lat_Long__c')
    
    latitude = latlong.get('latitude')
    longitude = latlong.get('longitude')
    
    if (city is None) or (country is None) or (state is None):
        return {}
    
    speech = "The venue for the event " + name + " is at " + venuename + ", which is at " + address + ", " + city + ", " + state + ", " + country
    
    slack_message = {
            "text": speech,
            "attachments": [
                {
                    "title": name + "Venue Location",
                    "title_link": "https://www.google.com/maps?q="+str(latitude)+","+str(longitude),
                    "color": "#36a64f",

                    "fields": [
                        {
                            "title": "Coordinates",
                            "value": str(latitude) + ", " + str(longitude),
                            "short": "true"
                        },
                        {
                            "title": "Address",
                            "value": city + ", " + state + ", " + country,
                            "short": "false"
                        }
                    ],

                    "thumb_url": icon
                }
            ]
    }
        
    facebook_message = {
        "attachment": {
            "type": "template",
            "payload": {
                "template_type": "generic",
                "elements": [
                    {
                        "title": name,
                        "subtitle": venuename + ", " + address + ", " + city + ", " + state,
                        "buttons": [
                            {
                                "type": "web_url",
                                "url": "https://www.google.com/maps?q="+str(latitude)+","+str(longitude),
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
        "data": {"facebook": facebook_message, "slack": slack_message},
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
