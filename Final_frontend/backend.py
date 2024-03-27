from flask import Flask, render_template,request,jsonify,url_for,session,redirect
import requests
# from flask_oauthlib.client import OAuth
from authlib.integrations.flask_client import OAuth
# from flask_oauth import OAuth
import folium
from polyline import decode
from bson import ObjectId
from pymongo import MongoClient
import json
import os
from functools import wraps


client = MongoClient("mongodb://localhost:27017/")
mydatabase = client.Trail 
mycollection=mydatabase['routes'] 

app = Flask(__name__)

oauth = OAuth(app)
app.secret_key = 'your_secret_key_here'
# app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=5)
# google_client_id = '779933776854-3jg4ja4b3kfh579179dg03inkqdme78r.apps.googleusercontent.com'
# google_client_secret = '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'
# google_redirect_uri = 'your_google_redirect_uri_here'

# oauth = OAuth(app)
# google = oauth.register(
#     'google',
#     consumer_key=google_client_id,
#     consumer_secret=google_client_secret,
#     request_token_params={
#         'scope': 'openid profile email',
#     },
#     base_url='https://www.googleapis.com/oauth2/v1/',
#     request_token_url=None,
#     access_token_method='POST',
#     access_token_url='https://accounts.google.com/o/oauth2/token',
#     authorize_url='https://accounts.google.com/o/oauth2/auth',
# )
google = oauth.register(
    name = 'google',
    client_id = '779933776854-3jg4ja4b3kfh579179dg03inkqdme78r.apps.googleusercontent.com',
    client_secret = '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',
    # access_token_url ='https://accounts.google.com/o/oauth2/token',
    access_token_params = None,
    # authorize_url = 'https://accounts.google.com/o/oauth2/auth',
    authorize_params = None,
    api_base_url = 'https://www.googleapis.com/oauth2/v1/',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid profile email'}
)

def login_required(func):
    def decorated_function(*args, **kwargs):
        if 'token' not in session:
            return redirect(url_for('loginn'))
        return func(*args, **kwargs)
    return decorated_function


@app.route('/')
def login_page():
    return render_template('login.html')


@app.route('/login')
def login():
    google = oauth.create_client('google')
    redirect_uri = url_for('authorize', _external=True)
    print('hi')
    return google.authorize_redirect(redirect_uri)
    

@app.route('/authorize')
def authorize():
    google = oauth.create_client('google')
    token = google.authorize_access_token()
    print("Received JWT token:", token)

    if token:
        session['token'] = token  
        print("Token stored in session:", session['token'])
    else:
        print("No token received")

    resp = google.get('userinfo', token=token)
    user_info = resp.json()
    return redirect('/home')

@app.route('/logout')
def logout():
    if 'token' in session:
        print("Token present in session:", session['token'])
    else:
        print("No token present in session")

    session.clear()  
    print("Session cleared")
    return redirect('/')

@app.route('/generate-route',methods = ['POST','GET'])

def generate_route_map():   
    if request.method == 'POST':
        data = request.json  
        result = mycollection.insert_one(data)  
        if result.inserted_id:
            return jsonify({"success": True, "message": "Route saved successfully."}), 201
        else:
            return jsonify({"success": False, "message": "Failed to save the route."}), 400
    return render_template('route_map.html')

@app.route('/home')
@login_required
def home():
    return render_template('home.html')



@app.route('/api/saved-routes', methods=['GET'])

def get_saved_routes():
    routes = mycollection.find()  
    routes_list = [{
        "startAddress": route.get("startAddress", ""),
        "endAddress": route.get("endAddress", ""),
        "id": str(route.get('_id', ""))
    } for route in routes]
    return jsonify(routes_list)

@app.route('/saved_route/<button_id>', methods=['GET'])
def saved_route(button_id: str):
    try:
        object_id = ObjectId(button_id)
        route = mycollection.find_one({"_id": object_id})
        
        if route:
            route_coordinates = route.get("routeCoordinates", [])
            start_address = route.get("startAddress", "")
            end_address = route.get("endAddress", "")
            return render_template('saved_route.html', route=route, route_coordinates=json.dumps(route_coordinates), start_address=start_address, end_address=end_address)
        else:
            return render_template('error.html', message='Route not found')
    except Exception as e:
        return render_template('error.html', message=str(e))

if __name__ == '__main__':
    app.run(debug=True)