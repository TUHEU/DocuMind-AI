from sqlalchemy import make_url

from app.core.config import Settings


def test_password_with_special_characters_is_parsed_correctly():
    s = Settings(db_user="root", db_password="p@ss:w/rd#1", db_host="localhost", db_name="idp_db")
    # the SQLAlchemy URL object keeps the password exactly as typed
    assert s.sqlalchemy_url.password == "p@ss:w/rd#1"
    assert s.sqlalchemy_url.host == "localhost"
    # the escaped string form also round-trips to the same password
    assert make_url(s.database_url).password == "p@ss:w/rd#1"
    assert make_url(s.database_url).host == "localhost"
