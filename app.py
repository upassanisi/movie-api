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


@app.route('/load-data', methods=['POST'])
def load_data_endpoint():
    file = request.files['file']
    if file.filename.endswith('.csv'):
        df = pd.read_csv(file)
    elif file.filename.endswith('.xlsx'):
        df = pd.read_excel(file)
    else:
        return jsonify({"error": "Unsupported file format"}), 400

    try:
        for _, row in df.iterrows():
            print(f"Processing row: {row.to_dict()}")  # Debug print

            # Handle director
            director_name = row['director']
            director = Director.query.filter_by(name=director_name).first()
            if not director:
                director = Director(name=director_name)
                db.session.add(director)
                db.session.commit()
                director = Director.query.filter_by(name=director_name).first()

            # Ensure rating is a float, else set to None or default value
            try:
                rating = float(row['avg_vote'])
            except (ValueError, TypeError):
                rating = None  # or set to a default value like 0.0

            # Handle movie
            movie = Movie.query.filter_by(title=row['title'], director_id=director.director_id).first()
            if not movie:
                movie = Movie(
                    title=row['title'],
                    release_year=row['year'],
                    genre=row['genre'],
                    rating=rating,
                    director_id=director.director_id
                )
                db.session.add(movie)
                db.session.commit()
                movie = Movie.query.filter_by(title=row['title'], director_id=director.director_id).first()

            # Ensure actors column is processed correctly
            if isinstance(row['actors'], str):
                actor_names = row['actors'].split(', ')
            else:
                actor_names = []  # or handle as needed

            # Handle actors and relationships
            for actor_name in actor_names:
                actor = Actor.query.filter_by(name=actor_name).first()
                if not actor:
                    actor = Actor(name=actor_name)
                    db.session.add(actor)
                    db.session.commit()
                    actor = Actor.query.filter_by(name=actor_name).first()

                # Check if the movie_actor relationship already exists
                movie_actor = MovieActor.query.filter_by(movie_id=movie.movie_id, actor_id=actor.actor_id).first()
                if not movie_actor:
                    movie_actor = MovieActor(movie_id=movie.movie_id, actor_id=actor.actor_id)
                    db.session.add(movie_actor)
                    db.session.commit()

        return jsonify({"message": "Data loaded successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


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
    app.run(debug=True)
