from flask import Flask, request, send_file, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import pandas as pd
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movies.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)


# Define the models
class Movie(db.Model):
    __tablename__ = 'movies'
    movie_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    release_year = db.Column(db.Integer)
    genre = db.Column(db.String(50))
    rating = db.Column(db.Float)
    director_id = db.Column(db.Integer, db.ForeignKey('directors.director_id'))


class Actor(db.Model):
    __tablename__ = 'actors'
    actor_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    birth_year = db.Column(db.Integer)
    nationality = db.Column(db.String(50))


class Director(db.Model):
    __tablename__ = 'directors'
    director_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    birth_year = db.Column(db.Integer)
    nationality = db.Column(db.String(50))


class MovieActor(db.Model):
    __tablename__ = 'movie_actor'
    movie_id = db.Column(db.Integer, db.ForeignKey('movies.movie_id'), primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('actors.actor_id'), primary_key=True)


# Load data endpoint
@app.route('/load-data', methods=['POST'])
def load_data_endpoint():
    file = request.files['file']
    if file.filename.endswith('.csv'):
        df = pd.read_csv(file)
    elif file.filename.endswith('.xlsx'):
        df = pd.read_excel(file)
    else:
        return "Unsupported file format", 400

    # Assuming the columns in the CSV/XLSX are Title, ReleaseYear, Genre, Rating, Director, Actors
    for _, row in df.iterrows():
        director = Director.query.filter_by(name=row['Director']).first()
        if not director:
            director = Director(name=row['Director'])
            db.session.add(director)
            db.session.commit()

        movie = Movie(
            title=row['Title'],
            release_year=row['ReleaseYear'],
            genre=row['Genre'],
            rating=row['Rating'],
            director_id=director.director_id
        )
        db.session.add(movie)
        db.session.commit()

        actors = row['Actors'].split(', ')
        for actor_name in actors:
            actor = Actor.query.filter_by(name=actor_name).first()
            if not actor:
                actor = Actor(name=actor_name)
                db.session.add(actor)
                db.session.commit()

            movie_actor = MovieActor(movie_id=movie.movie_id, actor_id=actor.actor_id)
            db.session.add(movie_actor)
    db.session.commit()
    return 'Data loaded successfully', 200


# Export data endpoint
@app.route('/export-data', methods=['GET'])
def export_data():
    query = db.session.query(Movie, Director, Actor).join(Director).join(MovieActor).join(Actor)

    title = request.args.get('title')
    genre = request.args.get('genre')
    director_name = request.args.get('director')
    actor_name = request.args.get('actor')

    if title:
        query = query.filter(Movie.title.like(f'%{title}%'))
    if genre:
        query = query.filter(Movie.genre.like(f'%{genre}%'))
    if director_name:
        query = query.filter(Director.name.like(f'%{director_name}%'))
    if actor_name:
        query = query.filter(Actor.name.like(f'%{actor_name}%'))

    data = []
    for movie, director, actor in query.all():
        data.append({
            'Title': movie.title,
            'ReleaseYear': movie.release_year,
            'Genre': movie.genre,
            'Rating': movie.rating,
            'Director': director.name,
            'Actor': actor.name
        })
    df = pd.DataFrame(data)
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    return Response(
        output,
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=movies.csv"}
    )


if __name__ == '__main__':
    app.run()
