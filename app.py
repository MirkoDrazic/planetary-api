from flask import Flask, jsonify, request, make_response
import os
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_jwt_extended import JWTManager, jwt_required, create_access_token
from flask_mail import Mail, Message
from flask_restplus import Api, Resource, fields

api = Api()

app = Flask(__name__)
api.init_app(app)
name_space = api.namespace('/', description='Main APIs')


basedir = os.path.abspath(os.path.dirname(__file__))

app.config.from_object("config.DevelopmentConfig")


db = SQLAlchemy(app)
ma = Marshmallow(app)
jwt = JWTManager(app)
mail = Mail(app)
from database_models import User, Planet, planet_schema, planets_schema, user_schema, users_schema

@app.cli.command('db_create')
def db_create():
    db.create_all()
    print('Database created!')


@app.cli.command('db_drop')
def db_drop():
    db.drop_all()
    print('Database dropped!')


@app.cli.command('db_seed')
def db_seed():
    mercury = Planet(planet_name='Mercury',
                     planet_type='Class D',
                     home_star='Sol',
                     mass=3.258e23,
                     radius=1516,
                     distance=35.98e6)

    venus = Planet(planet_name='Venus',
                     planet_type='Class K',
                     home_star='Sol',
                     mass=4.867e24,
                     radius=3760,
                     distance=67.24e6)

    earth = Planet(planet_name='Earth',
                     planet_type='Class M',
                     home_star='Sol',
                     mass=5.972e24,
                     radius=3959,
                     distance=92.96e6)

    db.session.add(mercury)
    db.session.add(venus)
    db.session.add(earth)

    test_user = User(first_name='William',
                     last_name='Herschell',
                     email='test@test.com',
                     password='P@ssw0rd')

    db.session.add(test_user)
    db.session.commit()
    print('Database seeded!')


@name_space.route('/hello_world')
class HelloWorld(Resource):
    def get(self):
        return 'Hello World!'


@name_space.route('/super_simple')
class SuperSimple(Resource):
    def get(self):
        return make_response(jsonify(message='Hello from the Planetary API.'), 200)


@name_space.route('/not_found')
class NotFound(Resource):
    def get(self):
        return make_response(jsonify(message='That resource was not found.'), 404)


@name_space.route('/parameters')
class Parameters(Resource):
    def get(self):
        name = request.args.get('name')
        age = int(request.args.get('age'))
        if age < 18:
            return make_response(jsonify(message='Sorry ' + name + ', you are not old enough.'), 401)
        else:
            return make_response(jsonify(message='Welcome ' + name + ', you are old enough!'))


@name_space.route('/url_variables/<string:name>/<int:age>')
class UrlVariables(Resource):
    def get(self, name: str, age: int):
        if age < 18:
            return make_response(jsonify(message='Sorry ' + name + ', you are not old enough.'), 401)
        else:
            return make_response(jsonify(message='Welcome ' + name + ', you are old enough!'))


@name_space.route('/planets')
class Planets(Resource):
    def get(self):
        planets_list = Planet.query.all()
        result = planets_schema.dump(planets_list)
        return make_response(jsonify(result))


register_fields = api.model('Register form', {
    'first_name': fields.String,
    'last_name': fields.String,
    'email': fields.String,
    'password': fields.String
})
@name_space.route('/register')
class Register(Resource):
    @api.expect(register_fields)
    def post(self):
        if request.is_json:
            email = request.json['email']
            first_name = request.json['first_name']
            last_name = request.json['last_name']
            password = request.json['password']
        else:
            email = request.form['email']
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            password = request.form['password']

        test = User.query.filter_by(email=email).first()
        if test:
            return make_response(jsonify(message='That email is already in use!'), 409)
        else:
            user = User(first_name=first_name,
                        last_name=last_name,
                        email=email,
                        password=password)
            db.session.add(user)
            db.session.commit()
            return make_response(jsonify(message='User created successfully!'), 201)


login_fields = api.model('Login form', {
    'email': fields.String,
    'password': fields.String
})


@name_space.route('/login')
class Login(Resource):
    @api.expect(login_fields)
    def post(self):
        if request.is_json:
            email = request.json['email']
            password = request.json['password']
        else:
            email = request.form['email']
            password = request.form['password']

        test = User.query.filter_by(email=email, password=password).first()
        if test:
            access_token = create_access_token(identity=email)
            return make_response(jsonify(message='Login succeeded!', access_tokena=access_token), 200)
        else:
            return make_response(jsonify(message='Bad email or password'), 401)


@name_space.route('/retrieve_password/<string:email>')
class RetrievePassword(Resource):
    def get(self, email: str):
        user = User.query.filter_by(email=email).first()
        if user:
            msg = Message("your planetary API password is:" + user.password,
                          sender="admin@planetary-api.com",
                          recipients=[email])
            mail.send(msg)
            return make_response(jsonify(message='Password sent to {}'.format(email)), 200)
        else:
            return make_response(jsonify(message='That email does not exist!'), 401)


@name_space.route('/planet_details/<int:planet_id>')
class PlanetDetails(Resource):
    def get(self, planet_id: int):
        planet = Planet.query.filter_by(planet_id=planet_id).first()
        if planet:
            result = planet_schema.dump(planet)
            return make_response(jsonify(result), 200)
        else:
            return make_response(jsonify(message='That planet does not exist!'), 404)


addPlanet_fields = api.model('Add planet form', {
    'planet_name': fields.String,
    'planet_type': fields.String,
    'home_star': fields.String,
    'mass': fields.Float,
    'radius': fields.Float,
    'distance': fields.Float
})


@jwt_required
@name_space.route('/add_planet')
class AddPlanet(Resource):
    @api.expect(addPlanet_fields)
    def post(self):
        planet_name = request.form['planet_name']
        test = Planet.query.filter_by(planet_name=planet_name).first()
        if test:
            return make_response(jsonify('There is already a planet bt that name'), 409)
        else:
            planet_type = request.form['planet_type']
            home_star = request.form['home_star']
            mass = float(request.form['mass'])
            radius = float(request.form['radius'])
            distance = float(request.form['distance'])

            new_planet = Planet(planet_name=planet_name,
                                planet_type=planet_type,
                                home_star=home_star,
                                mass=mass,
                                radius=radius,
                                distance=distance)

            db.session.add(new_planet)
            db.session.commit()
            return make_response(jsonify(message='You added a planet'), 201)

updatePlanet_fields = api.model('Update planet form', {
    'planet_id': fields.Integer,
    'planet_name': fields.String,
    'planet_type': fields.String,
    'home_star': fields.String,
    'mass': fields.Float,
    'radius': fields.Float,
    'distance': fields.Float
})


@jwt_required
@name_space.route('/update_planet')
class UpdatePlanet(Resource):
    @api.expect(updatePlanet_fields)
    def put(self):
        planet_id = int(request.form['planet_id'])
        planet = Planet.query.filter_by(planet_id=planet_id).first()
        if planet:
            planet.planet_name = request.form['planet_name']
            planet.planet_type = request.form['planet_type']
            planet.home_star = request.form['home_star']
            planet.mass = float(request.form['mass'])
            planet.radius = float(request.form['radius'])
            planet.distance = float(request.form['distance'])
            db.session.commit()
            return make_response(jsonify(message='You updated a planet!'), 202)
        else:
            return make_response(jsonify(message='That planet does not exist!'), 404)


@jwt_required
@name_space.route('/remove_planet/<int:planet_id>')
class RemovePlanet(Resource):
    def delete(self, planet_id: int):
        planet = Planet.query.filter_by(planet_id=planet_id).first()
        if planet:
            db.session.delete(planet)
            db.session.commit()
            return make_response(jsonify(message='You deleted a planet!'), 202)
        else:
            return make_response(jsonify(message='That planet was not there'), 404)


if __name__ == '__main__':
    app.run()