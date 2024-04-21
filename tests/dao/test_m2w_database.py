from unittest import TestCase
from unittest.mock import MagicMock

from src.dao.m2w_database import M2wDocumentHandler
from google.cloud import firestore

class MockDoc():
    def __init__(self) -> None:
        self.exists = True

class MockCollection():
    def document(self):
        return True

class TestM2wDocumentHandler(TestCase):
    def test_get_one_should_return_one_item(self):
        #given
        db = firestore.Client()
        doc = MockDoc()
        doc_ref = MagicMock(firestore.DocumentReference)
        doc_ref.get = MagicMock(return_value=doc)
        collection = MockCollection()
        collection.document = MagicMock(return_value=doc_ref)
        db.collection = MagicMock(return_value=collection)
        under_test = M2wDocumentHandler(db=db, collection="test", kind="test")

        #when
        response = under_test.get_one(id_="1")

        #then
        self.assertEqual(response, doc)