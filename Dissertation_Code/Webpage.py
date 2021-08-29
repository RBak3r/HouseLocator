        
from flask import Flask, render_template, request, redirect, url_for, json
import Algorithm_Flask_link_test_SI_17_08


app = Flask(__name__)

app.secret_key = "uom"

@app.route("/", methods = ["POST", "GET"]) #urlstring
def home():

        return render_template("Homepage.html")  

@app.route("/find-my-home", methods=["POST", "GET"])
def houseSearch():

    if request.method == "POST":
        
        return redirect(url_for(mapApp))
    
    else:
        return render_template("HouseSearch.html")
    
@app.route("/House-map", methods=["POST", "GET"])
def mapApp():
    
        GP = request.args.get("GP", None)
        Hsp = request.args.get("Hsp", None)
        GS = request.args.get("GS", None)
        SM = request.args.get("SM", None)
        Tr = request.args.get("Tr", None)
        Sch = request.args.get("Sch", None)
        Pb = request.args.get("Pb", None)
        FR = request.args.get("FR", None)
        AQ = request.args.get("AQ", None)
        Cr = request.args.get("Cr", None)
        PT = request.args.get("PT", None)
        MT = request.args.get("MT", None)
        BDmin = request.args.get("BDmin", None)
        BDmax = request.args.get("BDmax", None)
        PRmin = request.args.get("PRmin", None)
        PRmax = request.args.get("PRmax", None)
        LS = request.args.get("LS", None)
        Imp1Lat = request.args.get("placeLat1", None)
        Imp1Lng = request.args.get("placeLng1", None)
        Imp2Lat = request.args.get("placeLat2", None)
        Imp2Lng = request.args.get("placeLng2", None)
        radius = request.args.get("radius", None)

        homeMaster = Algorithm_Flask_link_test_SI_17_08.findHouse(GP, Hsp, GS, SM, Tr, Sch, Pb, FR, AQ, Cr, PT, MT, BDmin, BDmax, PRmin, PRmax, LS, Imp1Lat, Imp1Lng, Imp2Lat, Imp2Lng, radius)
        
        homeMasterJSON = homeMaster.to_json(na='null')
        
        return render_template("mapApp.html", homeMasterJSON = homeMasterJSON, criteriaValues=[GP, Hsp, GS, SM, Tr, FR, AQ, Cr, PT, MT, BDmin, BDmax, PRmin, PRmax, LS, Imp1Lat, Imp1Lng, Imp2Lat, Imp2Lng, radius])
    
        

@app.route("/FAQs")
def FAQs():
    return render_template("FAQs.html")
  
if __name__ == "__main__":
    app.run(debug=True)
    








