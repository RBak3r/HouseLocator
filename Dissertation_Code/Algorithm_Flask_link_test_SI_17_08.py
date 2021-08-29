

######################## 
######## Imports #######
########################
    
from json import loads # converts JSON string into a format that can be read by Python
from time import time as count_time # used to record the running time of the algorithm
from geopandas import read_file, GeoDataFrame, points_from_xy, clip # using for importing files, creating dataframes with geometry, getting cordinate points and clipping a dataframe to a geographical area
from pandas import DataFrame # Used to create dataframes (without geometry)
from zoopla import Zoopla # used for the Zoopla Property Listings API
from pickle import dump, load, HIGHEST_PROTOCOL # used to serialise dataframes
from pathlib import Path # used to check if a path directory exists
from shapely.geometry import Point, Polygon # For working with point and polygon geometries
import requests # Used to request data from APIs
from rtree import index # used to create a spatial index for dataframes
  
########################   
#### set start time ####
########################

start_time = count_time() 	

########################
###### API Keys ########
########################

ORSKey = '5b3ce3597851110001cf62480bd069acdadc433190a579fb3557c76a'

   

    
## Import User determined variables from interface form and used to weight algorithm ##

## Whole algorithm is in function so it can be called flask application ##

def findHouse(GP, Hsp, GS, SM, Tr, Sch, Pb, FR, AQ, Cr, PT, MT, BDmin, BDmax, PRmin, PRmax, LS, Imp1Lat, Imp1Lng, Imp2Lat, Imp2Lng, radius): 
    
    
    #######################
    #### Functions ########
    #######################
    
    ## Generator function to add records from each dataframe to spatial index ##
    # Generator used to increases the speed of loading the spatial index over the classic 'insert' method
        
    def idx_generator_function(data): 
	
        for i, obj in enumerate(data): 
            yield (i, obj.bounds, obj)
            
    ## Determines the closest points in each spatial index to each house ##
    
    def getNearest_Points(index, dataframe, locations):
            
        for id, home in homesPoints_df.iterrows():  # iterate through the rows each wih a property location
            nearestCriteria_index = list(index.nearest(home.geometry.bounds, 2))    # Find the index of the nearest 2 datapoints to each house
            nearestCriteria = GeoDataFrame(dataframe.iloc[nearestCriteria_index]['geometry'])   # Take the geometry of these 2 points from the wider dataframe
            for id, i in nearestCriteria.iterrows():                        # iterate through each of these 2 points
                locations.append([(i.iloc[0].y), (i.iloc[0].x)])            # append these points onto the main list of closest places
            
        
        return locations    # return this list
    
    ## For each house return the shortest journey to the closest criteria ##
    
    def getShortest_df(criterion_locations):        
        
        locations_criterionhome =  criterion_locations + home_locations  # create a combined list of properties and criterion locations
                        
        destinations_criterion = list(range(len(criterion_locations))) # create a list of positions that the matrix should consider (e.g. property-criteria not criteria-house)
        
        
        ### ORS Matrix API Call ###
        
        body = {"locations": locations_criterionhome, "destinations": destinations_criterion, "metrics": ["duration"]} # set inputs for API request
        
        headers = {
                'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
                'Authorization': ORSKey,
                'Content-Type': 'application/json; charset=utf-8'
                }
        
        criterion_matrixCall = requests.post(f'https://api.openrouteservice.org/v2/matrix/{transportMethod}', json=body, headers=headers) # call API request
        
        json_criterionmatrix = loads(criterion_matrixCall.text) # read returned json file
        
        criterionmatrix_list = json_criterionmatrix['durations'] #create a list of durations
        
        criterionmatrix_list = criterionmatrix_list[len(criterion_locations):] # for whatever the final list is. Cuts off houses-houses part
        
        shortest_criterion =[]
        
        for criterion_times in criterionmatrix_list:        # Append shortest times to empty list
            shortest_criterion.append(min(criterion_times))
            
        return shortest_criterion 
    
    
    ###########################
    #### User Preferences #####
    ###########################
    
    ## Take user provided values and convert from string (from JavaScript) to integers to be used as weightings ##
    
    GS = int(GS) # Green Space
    SM = int(SM) # Supermarkets
    Sch = int(Sch) # Schools
    Cr = int(Cr) # Crime
    GPs = int(GP) # GPs
    Hs = int(Hsp) # Hospitals
    Pb = int(Pb) # Public Houses
    AQ = int(AQ) # Air Quality
    FR = int(FR) # Flood Risk
    Tr = int(Tr) # Train Stations
    Imp1 = 5 # Important Place 1 - preset to highest weight
    Imp2 = 5 # Important Place 2 - preset to highest weight
    
    transportMethod = MT # Usual method of transport - used for some ORS routing decisions
    
    ###########################
    ### Important Locations ###
    ###########################
    
    ## User determined important locations such as workplace or freind's/family's homes ## 
    # Used as starting point for APIs and as a further criteria weightings 
    # Converted from string to float (number with lots of decimals)
          
    importantPlace_1 = Point(float(Imp1Lat), float(Imp1Lng))
    
    importantPlace_2 = Point(float(Imp2Lat), float(Imp2Lng))
      

    ## Greater Manchester bounding box. Used to clip some datasets ##
    
    GM_BB = Polygon([(-2.7303513, 53.3272247), (-1.909700, 53.326870), (-1.9078302, 53.68592), (-2.724717, 53.685322)])  
    
    ## Greater Manchester Specific Equidistance projection ##
    
    equalProj = "+proj=aeqd +lon_0=-2.2741699 +lat_0=53.5041236 +datum=WGS84 +units=m +no_defs" # Greater Manchetser Equidistance
    
    
    ############################
    ### House Specifications ###
    ############################
    
    ## User determined. Fed to Zoopla API to return appropriate properties ##
    
    radius = radius # search radius around important location 1 for properties
    propertyType = str(PT) # type of property (e.g. houses/flats)
    maxBeds = int(BDmax) # maximum number of beds
    minBeds = int(BDmin) # minimum number of beds
    maxPrice = int(PRmax) # maximum price of property - (can be rent/week or total price)
    minPrice = int(PRmin) # minimum price of property - (can be rent/week or total price)
    listingStatus = LS # listing Status (for sale/rent)
    
    
    ############################
    ### Import Criteria Data ###
    ############################
    
    ### Green space access points ###
        
    if not Path('../Diss_Data/Green_Space/GM_PublicGreenspaceaccesspoints.pkl').is_file():
        
        print("No Green Space file found, loading data (takes a long time).")
        
        GS_accessPoints = read_file("../Diss_Data/Green_Space/GM_PublicGreenspaceaccesspoints.shp").to_crs({'init': 'epsg:4326'})
        
        with open('../Diss_Data/Green_Space/GM_PublicGreenspaceaccesspoints.pkl', 'wb') as output:
                dump(GS_accessPoints, output, HIGHEST_PROTOCOL)      
    else:
        print("Green Space Pickle file found successfully, loading data.")
    
        with open('../Diss_Data/Green_Space/GM_PublicGreenspaceaccesspoints.pkl', 'rb') as input:
            GS_accessPoints = load(input)
       

        
    ### GPs data import ###
    
    if not Path('../Diss_Data/GPs/GPs.pkl').is_file(): # If pickle file doesn't exist: 
        
        print("No GPs file found, loading data (takes a long time).") # Let me know that it's not found and it may take a while
        
        gp = read_file("../Diss_Data/GPs/GPs.csv")
        
        gp_points = []
    
        for id, surgery in gp.iterrows(): # for every surgery within the GP data use the ORS geocoder API to get coordinates
            
            gpGeocode = requests.get(f'https://nominatim.openstreetmap.org/search?postalcode={surgery.Postcode}&limit=2&format=geojson')
            
            json_geocode = loads(gpGeocode.text)
            
            if len(json_geocode['features']) > 0:
    
                gp_points.append(Point(json_geocode['features'][0]['geometry']['coordinates'])) # add these coordinates to the file
                
            else:
                gp_points.append(None)
    
        gp = GeoDataFrame(gp, geometry=gp_points, crs='epsg:4326')
                      
        gp = gp[gp.geometry != None]
        
        with open('../Diss_Data/GPs/GPs.pkl', 'wb') as output:   # Create pickle file for future use
            dump(gp, output, HIGHEST_PROTOCOL)
          
    else:                                                           # If pickle file exists:
    	print("GP Pickle file found successfully, loading data.")    # Tell me it's been found
    
    	with open('../Diss_Data/GPs/GPs.pkl', 'rb') as input:        # Open pickle file and name it 
    		gp = load(input)
       
    
    ### Hospitals data import ###
    
    if not Path('../Diss_Data/Hospitals/hospitalsGM.pkl').is_file():
        
        print("No hospitals file found, loading data (takes a long time).")
        
        hospitals = read_file("../Diss_Data/Hospitals/hospitalsGM.csv")
        
        hospitals = GeoDataFrame(hospitals, geometry=points_from_xy(hospitals.Latitude, hospitals.Longitude), crs='epsg:4326')         
    
        with open('../Diss_Data/Hospitals/hospitalsGM.pkl', 'wb') as output:
            dump(hospitals, output, HIGHEST_PROTOCOL)
          
    else:
    	print("Hospital Pickle file found successfully, loading data.")
    
    	with open('../Diss_Data/Hospitals/hospitalsGM.pkl', 'rb') as input:
    		hospitals = load(input)
       
    
    ### Pub data import ###
    
    if not Path('../Diss_Data/Hospitality/pubs.pkl').is_file():
        
        print("No pubs file found, loading data (takes a long time).")
        
        pubs = read_file("../Diss_Data/Hospitality/pubs.csv")
        
        pubs = GeoDataFrame(pubs, geometry=points_from_xy(pubs.latitude, pubs.longitude), crs='epsg:4326')
         
        with open('../Diss_Data/Hospitality/pubs.pkl', 'wb') as output:
            dump(pubs, output, HIGHEST_PROTOCOL)
    
    else:
    	print("Pubs Pickle file found successfully, loading data.")
    
    	with open('../Diss_Data/Hospitality/pubs.pkl', 'rb') as input:
    		pubs = load(input)
    
    
    ### Schools data import ###
    
    
    if not Path('../Diss_Data/Schools/schoolsGM.pkl').is_file():
        
        print("No schools file found, loading data (takes a long time).")
        
        schools = read_file("../Diss_Data/Schools/schoolsGM.csv").to_crs(equalProj)
        
        sch_points = []
    
        for id, school in schools.iterrows(): # for every surgery within the GP data use the ORS geocoder API to get coordinates
    
            #print(gp.Postcode.to_string(index=False))
            
            #print(school.field_11)
            
            schGeocode = requests.get(f'https://nominatim.openstreetmap.org/search?postalcode={school.field_11}&limit=2&format=geojson')
            
            #print(gpGeocode.text)
            
            sch_json_geocode = loads(schGeocode.text)
            print(sch_json_geocode)
            
            if len(sch_json_geocode['features'])>0:
    
                sch_points.append(Point(sch_json_geocode['features'][0]['geometry']['coordinates'])) # add these coordinates to the file
    
            else:
                sch_points.append(None)
    
        schools = GeoDataFrame(schools, geometry=sch_points)
        
        with open('../Diss_Data/Schools/schoolsGM.pkl', 'wb') as output:
            dump(schools, output, HIGHEST_PROTOCOL)
          
    else:
    	print("Hospital Pickle file found successfully, loading data.")
    
    	with open('../Diss_Data/Schools/schoolsGM.pkl', 'rb') as input:
    		schools = load(input)
    
    
    ### Supermarkets data import ###
    
    if not Path('../Diss_Data/Supermarkets/SupermarketsGM.pkl').is_file():
        
        print("No supermarkets file found, loading data (takes a long time).")
        
        supermarkets = read_file("../Diss_Data/Supermarkets/SupermarketsGM.csv")
        
        supermarkets = GeoDataFrame(supermarkets, geometry=points_from_xy(supermarkets.lat_wgs, supermarkets.long_wgs))  
        
        with open('../Diss_Data/Supermarkets/SupermarketsGM.pkl', 'wb') as output:
            dump(supermarkets, output, HIGHEST_PROTOCOL)
          
    else:
    	print("Supermarket Pickle file found successfully, loading data.")
    
    	with open('../Diss_Data/Supermarkets/SupermarketsGM.pkl', 'rb') as input:
    		supermarkets = load(input)
    
    
    ### Air Quality data import ###
    
    if not Path('../Diss_Data/Air_Pollution/Air_Quality_GM.pkl').is_file():
        
        print("No Air Quality file found, loading data (takes a long time).")
        
        airQuality = read_file("../Diss_Data/Air_Pollution/Air_Quality_GM.csv")
        
        airQuality = GeoDataFrame(airQuality, geometry=points_from_xy(airQuality.Latitude, airQuality.Longitude))
        
        with open('../Diss_Data/Air_Pollution/Air_Quality_GM.pkl', 'wb') as output:
            dump(airQuality, output, HIGHEST_PROTOCOL)
          
    else:
    	print("Air Quality file found successfully, loading data.")
    
    	with open('../Diss_Data/Air_Pollution/Air_Quality_GM.pkl', 'rb') as input:
    		airQuality = load(input)
    
    
    ### Train Stations data import ###
    
    if not Path('../Diss_Data/Transport/RailReferences.pkl').is_file():
        
        print("No train stations file found, loading data (takes a long time).")
        
        trainStations = read_file("../Diss_Data/Transport/RailReferences.csv")
        
        trainStations = GeoDataFrame(trainStations, geometry=points_from_xy(trainStations.latitude, trainStations.longitude))
        
        with open('../Diss_Data/Transport/RailReferences.pkl', 'wb') as output:
            dump(trainStations, output, HIGHEST_PROTOCOL)
          
    else:
    	print("Train Station Pickle file found successfully, loading data.")
    
    	with open('../Diss_Data/Transport/RailReferences.pkl', 'rb') as input:
    		trainStations = load(input)
    
    
    ### Flood Risk data import ###
    
    if not Path('../Diss_Data/Flood_Risk/Surface_Water_Flood_Risk_Exposure_Grid_People_Sensitivity_Grid.pkl').is_file():
        
        print("No flood risk file found, loading data (takes a long time).")
        
        floodRisk = read_file("../Diss_Data/Flood_Risk/Surface_Water_Flood_Risk_Exposure_Grid_People_Sensitivity_Grid.shp").to_crs({'init': 'epsg:4326'})
    
        floodRisk = clip(floodRisk, GM_BB)
        
        with open('../Diss_Data/Flood_Risk/Surface_Water_Flood_Risk_Exposure_Grid_People_Sensitivity_Grid.pkl', 'wb') as output:
            dump(floodRisk, output, HIGHEST_PROTOCOL)
          
    else:
    	print("Flood Risk Pickle file found successfully, loading data.")
    
    	with open('../Diss_Data/Flood_Risk/Surface_Water_Flood_Risk_Exposure_Grid_People_Sensitivity_Grid.pkl', 'rb') as input:
    		floodRisk = load(input)
    
    
    
    ##################
    ### Zoopla API ###
    ##################
    
    zoopla = Zoopla(api_key='kycjtpbw76xapnkhuyfvvp66') # Initiate API
    
    search = zoopla.property_listings({                 # Give API the user's property criteria
        'radius': radius,
        'property_type': propertyType,
        'maximum_beds': maxBeds,
        'minimum_beds': minBeds,
        'maximum_price': maxPrice,
        'minimum_price': minPrice,
        'listing_status': listingStatus,
        'include_rented': '0',
        'include_sold': '0',
        'latitude': f"{importantPlace_1.x}",
        'longitude': f"{importantPlace_1.y}",
        'page_size': '15',
        'order_by': 'age'
    })        
    
    homesPoints =[]     # Inititate list for geometry point of each property
    possibleHomes = []  # Initiiate list to hold info for each property
    
    
    for possibleHome in search.listing:    # For each property that has been returned get points and create a list
        
        homeCoords = Point(possibleHome.latitude, possibleHome.longitude) # Get the coordinates of each property
        
        homesPoints += [homeCoords]
    
        homeInfo = [{"Listing id": possibleHome.listing_id, "Property type": possibleHome.property_type, "Street name": possibleHome.street_name, "Price":possibleHome.price, "Coords": (possibleHome.latitude, possibleHome.longitude), "Details url": possibleHome.details_url, "Description": possibleHome.short_description, "Image": possibleHome.image_url}]
        
        possibleHomes += homeInfo
    
    
    ### Creating the Master Dataframe ###
    
    homeMaster_df = GeoDataFrame(data = possibleHomes, geometry=homesPoints) # Create with info about each house and geometry of each point location
    
    criteria_headers=[{"Crime number":None, "Crime rank":None, "Hospital dist":None, "Hospital rank":None,	"GP dist":None, "GP rank":None,	"Supermarket dist": None, "Supermarket rank":None, "School rank":None,	"Train station dist":None, "Train station rank":None,	"Pub dist":None, "Pub rank":None, "Flood Risk":None, "Flood rank":None, "Air Quality":None, "Air Quality rank":None, "Green Space dist":None, "Green Space rank":None, "Imp1 dist":None, "Imp1 rank":None, "Imp2 dist":None, "Imp2 rank":None,	"Home score":None, "Master rank":None}] # Additional headers for each criteria to be added to master DF
    
    homeMaster_df = homeMaster_df.append(criteria_headers)  # Add headers to master DF 
    
     
    ### Crime ###
    
    crime_dict = []                           # initiate list to give each returned property a value (will be based on it's location to or value for datasets)
    
    
    for home in homesPoints:
        
        crimeCall = requests.post(f'https://data.police.uk/api/crimes-street/all-crime?lat={home.x}&lng={home.y}&date=2020-05')   # call the crime API and return crime data from the location of the property + 1 mile radius on a specified date
            
        json_crime = loads(crimeCall.text)
                     
        crime_dict += [{"Crime number": len(json_crime)}]
        
    crime_df = DataFrame(crime_dict)
    crime_df['Crime rank'] = crime_df['Crime number'].rank(ascending=True, method='min' )
    homeMaster_df['Crime number'] = crime_df['Crime number']
    homeMaster_df['Crime rank'] = crime_df['Crime rank']
    
    
    home_locations = [[point.y, point.x] for point in homesPoints]

    homesPoints_df = GeoDataFrame(range(len(search.listing)), geometry = homesPoints) # Create a dataframe of homesPoints so that it can be used with iterrows
    
    
    ### Hospitals ###
        
    hosp_locations = []
    
    hosp_idx = index.Index(idx_generator_function(hospitals.geometry))
    
    hosp_locations = getNearest_Points(hosp_idx, hospitals, hosp_locations)
    
    shortest_hosp = getShortest_df(hosp_locations)
    
    shortest_hosp_df = DataFrame(shortest_hosp, columns=['Hospital dist'])
    shortest_hosp_df['Hospital rank'] = shortest_hosp_df['Hospital dist'].rank(ascending=False)
    homeMaster_df['Hospital dist'] = shortest_hosp_df['Hospital dist']
    homeMaster_df['Hospital rank'] = shortest_hosp_df['Hospital rank']
    
    
    
    ### GPs ### 
    
    gp_locations = []
    
    GP_idx = index.Index(idx_generator_function(gp.geometry))
       
    gp_locations = getNearest_Points(GP_idx, gp, gp_locations)
    
    gp_locations = [([y,x]) for x,y in gp_locations]
    
    shortest_gp = getShortest_df(gp_locations)
        
    shortest_gp_df = DataFrame(shortest_gp, columns=['GP dist'])
    shortest_gp_df['GP rank'] = shortest_gp_df['GP dist'].rank(ascending=False)
    homeMaster_df['GP dist'] = shortest_gp_df['GP dist']
    homeMaster_df['GP rank'] = shortest_gp_df['GP rank']
    
    
    
    ### Supermarkets ###
    
    market_locations = []
    
    SM_idx = index.Index(idx_generator_function(supermarkets.geometry))
    
    market_locations = getNearest_Points(SM_idx, supermarkets, market_locations)
    
    shortest_market = getShortest_df(market_locations)
    
    shortest_market_df = DataFrame(shortest_market, columns=['Supermarket dist'])
    homeMaster_df['Supermarket dist'] = shortest_market_df['Supermarket dist']
    shortest_market_df['Supermarket rank'] = shortest_market_df['Supermarket dist'].rank(ascending=False)
    homeMaster_df['Supermarket rank'] = shortest_market_df['Supermarket rank']   
    
    
    
    ### Train Stations ###
    
    transportMethod = 'foot-walking' # Lock transport method to walking. Don't use user selection
    
    train_locations = []
    
    Tr_idx = index.Index(idx_generator_function(trainStations.geometry))
    
    train_locations = getNearest_Points(Tr_idx, trainStations, train_locations)
    
    shortest_train = getShortest_df(train_locations)
    
    shortest_train_df = DataFrame(shortest_train, columns=['Train station dist'])
    homeMaster_df['Train station dist'] = shortest_train_df['Train station dist']
    shortest_train_df['Train station rank'] = shortest_train_df['Train station dist'].rank(ascending=False)
    homeMaster_df['Train station rank'] = shortest_train_df['Train station rank']
    
    
    ### Public Houses ###
    
    pub_locations = []
    
    Pub_idx = index.Index(idx_generator_function(pubs.geometry))
    
    pub_locations = getNearest_Points(Pub_idx, pubs, pub_locations)
    
    shortest_pub = getShortest_df(pub_locations)
    
    shortest_pub_df = DataFrame(shortest_pub, columns=['Pub dist'])
    homeMaster_df['Pub dist'] = shortest_pub_df['Pub dist']
    shortest_pub_df['Pub rank'] = shortest_pub_df['Pub dist'].rank(ascending=False)
    homeMaster_df['Pub rank'] = shortest_pub_df['Pub rank']
    
    
    ### Important places ###
    
    transportMethod = 'driving-car' # Put transport method back to user selection
    
    ### Imp 1 ###
    
    imp1_location = [(importantPlace_1.y, importantPlace_1.x)]
    
    shortest_imp1 = getShortest_df(imp1_location)
    
    shortest_imp1_df = DataFrame(shortest_imp1, columns=['Imp1 dist'])
    homeMaster_df['Imp1 dist'] = shortest_imp1_df['Imp1 dist']
    shortest_imp1_df['Imp1 rank'] = shortest_imp1_df['Imp1 dist'].rank(ascending=False)
    homeMaster_df['Imp1 rank'] = shortest_imp1_df['Imp1 rank']
    
    
    ### Imp 2 ###
    
    imp2_location = [(importantPlace_2.y, importantPlace_2.x)]
    
    shortest_imp2 = getShortest_df(imp2_location)
    
    shortest_imp2_df = DataFrame(shortest_imp2, columns=['Imp2 dist'])
    homeMaster_df['Imp2 dist'] = shortest_imp2_df['Imp2 dist']
    shortest_imp2_df['Imp2 rank'] = shortest_imp2_df['Imp2 dist'].rank(ascending=False)
    homeMaster_df['Imp2 rank'] = shortest_imp2_df['Imp2 rank']
    
    
    ### Green Space ###
        
    GS_locations = []
    
    GS_idx = index.Index(idx_generator_function(GS_accessPoints.geometry))
    
    GS_locations = getNearest_Points(GS_idx, GS_accessPoints, GS_locations)
    
    GS_locations = [([y,x]) for x,y in GS_locations]
    
    shortest_GS = getShortest_df(GS_locations)
    
    shortest_GS_df = DataFrame(shortest_GS, columns=['Green Space dist'])
    homeMaster_df['Green Space dist'] = shortest_GS_df['Green Space dist']
    shortest_GS_df['Green Space rank'] = shortest_GS_df['Green Space dist'].rank(ascending=False)
    homeMaster_df['Green Space rank'] = shortest_GS_df['Green Space rank']
    
    
    ### Flood Risk ###
    
    nearest_FR_value = []
    
    floodRisk = floodRisk.reset_index(drop=True) # Reset Flood Risk index
      
    FR_idx = index.Index(idx_generator_function(floodRisk.geometry))
    
    for id, house in homesPoints_df.iterrows():
        nearest_FR_index = list(FR_idx.nearest(house.geometry.bounds, 1))[0]   
        nearest_FR = floodRisk.iloc[nearest_FR_index] 
        nearest_FR_value.append(nearest_FR['res_1000'])    
    
    FR_value_df = DataFrame(nearest_FR_value, columns=['Flood Risk'])
    homeMaster_df['Flood Risk'] = FR_value_df['Flood Risk']
    FR_value_df['Flood rank'] = FR_value_df['Flood Risk'].rank(ascending=False)
    homeMaster_df['Flood rank'] = FR_value_df['Flood rank']
    
    
    ### Air Quality ###
    
    nearest_AQ_value = []
    
    AQ_idx = index.Index(idx_generator_function(airQuality.geometry))
    
    for id, house in homesPoints_df.iterrows():
        nearest_AQ_index = list(AQ_idx.nearest(house.geometry.bounds, 1))[0]
        nearest_AQ = airQuality.iloc[nearest_AQ_index] 
        nearest_AQ_value.append(nearest_AQ['NO2'])    
    
    AQ_value_df = DataFrame(nearest_AQ_value, columns=['Air Quality'])
    homeMaster_df['Air Quality'] = AQ_value_df['Air Quality']
    AQ_value_df['Air Quality rank'] = AQ_value_df['Air Quality'].rank(ascending=False)
    homeMaster_df['Air Quality rank'] = AQ_value_df['Air Quality rank']
    
    
    ### Schools ###
        
    Sch_locations = []
         
    Sch_idx = index.Index(idx_generator_function(schools.geometry))
    
    Sch_locations = getNearest_Points(Sch_idx, schools, Sch_locations)
    
    Sch_locations = [([y,x]) for x,y in Sch_locations]
    
    shortest_Sch = getShortest_df(Sch_locations)
    
    shortest_Sch_df = DataFrame(shortest_Sch, columns=['School dist'])
    homeMaster_df['School dist'] = shortest_Sch_df['School dist']
    shortest_Sch_df['School rank'] = shortest_Sch_df['School dist'].rank(ascending=False)
    homeMaster_df['School rank'] = shortest_Sch_df['School rank']
    
    ###
    
    
    homeMaster_df['Home score'] = ((homeMaster_df['Hospital rank'] * Hs) + (homeMaster_df['GP rank'] * GPs) + (homeMaster_df['Crime rank'] * Cr) + (homeMaster_df['Train station rank'] * Tr) + (homeMaster_df['Green Space rank'] * GS) + (homeMaster_df['Supermarket rank'] * SM) + (homeMaster_df['Pub rank'] * Pb) + (homeMaster_df['Air Quality rank'] * AQ ) + (homeMaster_df['Flood rank'] * FR ) + (homeMaster_df['Imp1 rank'] * Imp1) + (homeMaster_df['Imp2 rank'] * Imp2) + (homeMaster_df['School rank'] * Sch))
       
    homeMaster_df = homeMaster_df[:len(search.listing)]
    
    homeMaster_df['Master rank'] = homeMaster_df['Home score'].rank(ascending=True, method = 'first')
      
    
    homeMaster_df['Lat'] = homeMaster_df['geometry'].x
    homeMaster_df['Long'] = homeMaster_df['geometry'].y
    
    homeMaster_df = homeMaster_df.sort_values('Master rank', ascending=False)
    
    
    # Re-rank the houses out of the sliced list
    
    homeMaster_df['Hospital rank'] = homeMaster_df['Hospital rank'].rank(ascending=True, method = 'max')
    homeMaster_df['GP rank'] = homeMaster_df['GP rank'].rank(ascending=True, method = 'max')
    homeMaster_df['Crime rank'] = homeMaster_df['Crime rank'].rank(ascending=True, method = 'max')
    homeMaster_df['Train station rank'] = homeMaster_df['Train station rank'].rank(ascending=True, method = 'max')
    homeMaster_df['Green Space rank'] = homeMaster_df['Green Space rank'].rank(ascending=True, method = 'max')
    homeMaster_df['Supermarket rank'] = homeMaster_df['Supermarket rank'].rank(ascending=True, method = 'max')
    homeMaster_df['Pub rank'] = homeMaster_df['Pub rank'].rank(ascending=True, method = 'max')
    homeMaster_df['Flood rank'] = homeMaster_df['Flood rank'].rank(ascending=True, method = 'max')
    homeMaster_df['Air Quality rank'] = homeMaster_df['Air Quality rank'].rank(ascending=True, method = 'max')
    
    return homeMaster_df

    # report runtime
    print(f"completed in: {count_time() - start_time} seconds")	# NO CODE BELOW HERE
    
