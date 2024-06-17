import os
import pytest
from io import BytesIO
from app import app, db, Movie, Director, Actor, MovieActor


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()


def test_load_data_csv(client):
    data = """Title,ReleaseYear,Genre,Rating,Director,Actors
              Inception,2010,Action,8.8,Christopher Nolan,Leonardo DiCaprio, Joseph Gordon-Levitt
              The Matrix,1999,Science Fiction,8.7,Lana Wachowski, Keanu Reeves, Laurence Fishburne"""
    response = client.post('/load-data', data={'file': (BytesIO(data.encode()), 'movies.csv')},
                           content_type='multipart/form-data')
    assert response.status_code == 200
    assert b'Data loaded successfully' in response.data

    # Check if data is loaded correctly
    movies = Movie.query.all()
    assert len(movies) == 2
    assert movies[0].title == 'Inception'
    assert movies[1].title == 'The Matrix'


def test_export_data(client):
    director = Director(name='Christopher Nolan')
    db.session.add(director)
    db.session.commit()

    movie = Movie(title='Inception', release_year=2010, genre='Action', rating=8.8, director_id=director.director_id)
    db.session.add(movie)
    db.session.commit()

    actor = Actor(name='Leonardo DiCaprio')
    db.session.add(actor)
    db.session.commit()

    movie_actor = MovieActor(movie_id=movie.movie_id, actor_id=actor.actor_id)
    db.session.add(movie_actor)
    db.session.commit()

    response = client.get('/export-data')
    assert response.status_code == 200
    assert 'Inception' in response.data.decode()
    assert 'Christopher Nolan' in response.data.decode()
    assert 'Leonardo DiCaprio' in response.data.decode()


def test_export_data_with_filters(client):
    director1 = Director(name='Christopher Nolan')
    director2 = Director(name='Lana Wachowski')
    db.session.add(director1)
    db.session.add(director2)
    db.session.commit()

    movie1 = Movie(title='Inception', release_year=2010, genre='Action', rating=8.8, director_id=director1.director_id)
    movie2 = Movie(title='The Matrix', release_year=1999, genre='Science Fiction', rating=8.7,
                   director_id=director2.director_id)
    db.session.add(movie1)
    db.session.add(movie2)
    db.session.commit()

    actor1 = Actor(name='Leonardo DiCaprio')
    actor2 = Actor(name='Keanu Reeves')
    db.session.add(actor1)
    db.session.add(actor2)
    db.session.commit()

    movie_actor1 = MovieActor(movie_id=movie1.movie_id, actor_id=actor1.actor_id)
    movie_actor2 = MovieActor(movie_id=movie2.movie_id, actor_id=actor2.actor_id)
    db.session.add(movie_actor1)
    db.session.add(movie_actor2)
    db.session.commit()

    response = client.get('/export-data?director=Christopher Nolan')
    assert response.status_code == 200
    assert 'Inception' in response.data.decode()
    assert 'The Matrix' not in response.data.decode()


def test_load_data_invalid_file(client):
    data = """Invalid Data"""
    response = client.post('/load-data', data={'file': (BytesIO(data.encode()), 'movies.txt')},
                           content_type='multipart/form-data')
    assert response.status_code == 400
    assert b'Unsupported file format' in response.data
