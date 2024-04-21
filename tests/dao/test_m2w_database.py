from unittest import TestCase
from unittest.mock import MagicMock

from src.dao.m2w_database import M2WDatabaseException, M2wDocumentHandler, M2wGroupHandler, M2wMovieHandler, M2wUserHandler
from google.cloud import firestore

class TestM2wDocumentHandler(TestCase):
    def test_get_one_should_return_one_item(self):
        #given
        db = firestore.Client()
        doc = MagicMock(firestore.DocumentSnapshot)
        doc.exists = True
        doc_ref = MagicMock(firestore.DocumentReference)
        doc_ref.get = MagicMock(return_value=doc)
        collection = MagicMock(firestore.CollectionReference)
        collection.document = MagicMock(return_value=doc_ref)
        db.collection = MagicMock(return_value=collection)
        under_test = M2wDocumentHandler(db=db, collection="test", kind="test")

        #when
        response = under_test.get_one(id_="1")

        #then
        self.assertEqual(response, doc)
        db.collection.assert_called_with("test")
        collection.document.assert_called_with("1")

    def test_get_one_should_raise_exception_if_document_is_missing(self):
        #given
        db = firestore.Client()
        doc = MagicMock(firestore.DocumentSnapshot)
        doc.exists = False
        doc_ref = MagicMock(firestore.DocumentReference)
        doc_ref.get = MagicMock(return_value=doc)
        collection = MagicMock(firestore.CollectionReference)
        collection.document = MagicMock(return_value=doc_ref)
        db.collection = MagicMock(return_value=collection)
        under_test = M2wDocumentHandler(db=db, collection="test", kind="test")

        #when
        with self.assertRaises(M2WDatabaseException) as context:
            response = under_test.get_one(id_="1")

        #then
        self.assertIsInstance(context.exception, M2WDatabaseException)
        db.collection.assert_called_with("test")
        collection.document.assert_called_with("1")


    def test_get_all_should_return_a_generator(self):
        #given
        db = firestore.Client()
        collection = MagicMock(firestore.CollectionReference)
        collection.stream = MagicMock(return_value=range(5))
        db.collection = MagicMock(return_value=collection)
        under_test = M2wDocumentHandler(db=db, collection="test", kind="test")

        #when
        response = under_test.get_all()

        #then
        for elem in response:
            self.assertIn(elem, [0, 1, 2, 3, 4])
        db.collection.assert_called_with("test")

    def test_set_data_should_return_write_results(self):
        #given
        db = firestore.Client()
        doc_ref = MagicMock(firestore.DocumentReference)
        doc_ref.set = MagicMock(return_value={'success':True})
        collection = MagicMock(firestore.CollectionReference)
        collection.document = MagicMock(return_value=doc_ref)
        db.collection = MagicMock(return_value=collection)
        under_test = M2wDocumentHandler(db=db, collection="test", kind="test")

        #when
        response = under_test.set_data(id_="1", data={"A":1})

        #then
        self.assertEqual(response, {'success':True})
        db.collection.assert_called_with("test")
        collection.document.assert_called_with("1")
        doc_ref.set.assert_called_with(document_data={"A":1}, merge=True)

    def test_delete_should_return_boolean(self):
        #given
        db = firestore.Client()
        doc_ref = MagicMock(firestore.DocumentReference)
        doc_ref.delete = MagicMock(return_value=True)
        collection = MagicMock(firestore.CollectionReference)
        collection.document = MagicMock(return_value=doc_ref)
        db.collection = MagicMock(return_value=collection)
        under_test = M2wDocumentHandler(db=db, collection="test", kind="test")

        #when
        response = under_test.delete(id_="1")

        #then
        self.assertEqual(response, True)
        db.collection.assert_called_with("test")
        collection.document.assert_called_with("1")
        doc_ref.delete.assert_called_with()

class TestM2wUserHandler(TestCase):
    def test_get_blocklist_should_return_collection_reference(self):
        #given
        db = firestore.Client()
        doc = MagicMock(firestore.DocumentSnapshot)
        doc.exists = True
        doc_ref = MagicMock(firestore.DocumentReference)
        doc_ref.get = MagicMock(return_value=doc)
        doc_ref.collection = MagicMock(return_value="success")
        collection = MagicMock(firestore.CollectionReference)
        collection.document = MagicMock(return_value=doc_ref)
        db.collection = MagicMock(return_value=collection)
        under_test = M2wUserHandler(db=db)

        #when
        response = under_test.get_blocklist(user_id="1")

        #then
        self.assertEqual(response, "success")
        db.collection.assert_called_with('users')
        collection.document.assert_called_with("1")
        doc_ref.collection.assert_called_with('blocklist')

    def test_get_blocklist_should_raise_exception_if_blocklist_missing(self):
        #given
        db = firestore.Client()
        doc = MagicMock(firestore.DocumentSnapshot)
        doc.exists = False
        doc_ref = MagicMock(firestore.DocumentReference)
        doc_ref.get = MagicMock(return_value=doc)
        doc_ref.collection = MagicMock(return_value="success")
        collection = MagicMock(firestore.CollectionReference)
        collection.document = MagicMock(return_value=doc_ref)
        db.collection = MagicMock(return_value=collection)
        under_test = M2wUserHandler(db=db)

        #when
        with self.assertRaises(M2WDatabaseException) as context:
            response = under_test.get_blocklist("1")

        #then
        self.assertIsInstance(context.exception, M2WDatabaseException)
        db.collection.assert_called_with("users")
        collection.document.assert_called_with("1")

class TestM2wMovieHandler(TestCase):
    def test(self):
        pass

class TestM2wGroupHandler(TestCase):
    def test(self):
        pass