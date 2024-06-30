import sys
import os
import requests
import datetime

from flask import Flask, render_template, request, redirect, flash, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_envvar('FLASK_CONF_VAR')
app.config['SECRET_KEY'] = os.urandom(24)
db = SQLAlchemy(app)


class City(db.Model):
    __tablename__ = 'city'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    def __repr__(self):
        return f'<City {self.name}>'


with app.app_context():
    db.drop_all()
    db.create_all()


def make_blueprint(city_name):
    try:
        api_key = os.environ["API_KEY"]
        api_url = os.environ["API_URL"]
    except KeyError:
        sys.exit("API key(s) missing from environmental variables")
    try:
        api_response = requests.get(api_url, params={'q': city_name, 'units': 'metric', 'appid': api_key})
        return api_response
    except (Exception, requests.exceptions.RequestException) as e:
        print(e)
        return redirect('/')


def make_city(response_object):
    response_object_dict = response_object.json()
    try:
        weather_dict = {'name': response_object_dict['name'],
                        'temp': round(response_object_dict['main']['temp']),
                        'state': response_object_dict['weather'][0]['main'],
                        'daytime': daytime_str(get_local_hour(response_object_dict['timezone']))}
        return weather_dict
    except (NameError, KeyError) as e:
        print(e)
        return redirect('/')


def get_local_hour(timezone):
    return (datetime.datetime.utcnow() + datetime.timedelta(seconds=timezone)).hour


def daytime_str(h):
    return "card night" if 22 <= h <= 23 or 0 <= h <= 3 else "card day" if 10 <= h <= 17 else "card evening-morning"


@app.route('/delete', methods=['GET', 'POST'])
def delete():
    db.session.delete(find_city(request.form['city_name']))
    db.session.commit()
    return redirect('/')


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('index.html', cities=make_city_coll())
    elif request.method == 'POST':
        if find_city(request.form['city_name']):
            flash('The city has already been added to the list!')
            return redirect('/')
        response_obj = make_blueprint(request.form['city_name'])
        if response_obj.status_code != 200:
            flash("The city doesn't exist!")
            return redirect('/')
        db.session.add(City(name=request.form['city_name']))
        db.session.commit()
        return redirect('/')


def find_city(city_name):
    with app.app_context():
        return City.query.filter(City.name == city_name).first()


def get_db_cities():
    with app.app_context():
        return City.query.all()


def make_city_coll():
    return [make_city(make_blueprint(city.name)) for city in get_db_cities()]


if __name__ == '__main__':
    if len(sys.argv) > 1:
        arg_host, arg_port = sys.argv[1].split(':')
        app.run(host=arg_host, port=arg_port)
    else:
        app.run()
