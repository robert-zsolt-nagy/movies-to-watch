from unittest import TestCase
from unittest.mock import MagicMock

from google.cloud import firestore

from src.dao.m2w_database import M2WDatabaseException, M2wDocumentHandler, M2wGroupHandler, M2wMovieHandler, \
    M2wUserHandler


class TestM2wDocumentHandler(TestCase):
    def test_get_one_should_return_one_item(self):
        #given
        db = MagicMock(firestore.Client)
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
        db = MagicMock(firestore.Client)
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
        db = MagicMock(firestore.Client)
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
        db = MagicMock(firestore.Client)
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
        db = MagicMock(firestore.Client)
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
        db = MagicMock(firestore.Client)
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
        db = MagicMock(firestore.Client)
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
            under_test.get_blocklist("1")

        #then
        self.assertIsInstance(context.exception, M2WDatabaseException)
        db.collection.assert_called_with("users")
        collection.document.assert_called_with("1")

class TestM2wMovieHandler(TestCase):
    def test_remove_from_blocklist_should_return_boolean(self):
        #given
        db = MagicMock(firestore.Client)
        doc = MagicMock(firestore.DocumentReference)
        doc.delete = MagicMock(return_value="success")
        blocklist = MagicMock(firestore.CollectionReference)
        blocklist.document = MagicMock(return_value=doc)
        under_test = M2wMovieHandler(db=db)

        #when
        response = under_test.remove_from_blocklist(
            movie_id="1",
            blocklist=blocklist
        )

        #then
        self.assertEqual(response, True)
        blocklist.document.assert_called_with("1")

    def test_add_to_blocklist_should_return_boolean(self):
        #given
        db = MagicMock(firestore.Client)
        doc = MagicMock(firestore.DocumentReference)
        doc.set = MagicMock(return_value="success")
        blocklist = MagicMock(firestore.CollectionReference)
        blocklist.document = MagicMock(return_value=doc)
        under_test = M2wMovieHandler(db=db)

        #when
        response = under_test.add_to_blocklist(
            movie_id="1",
            blocklist=blocklist,
            movie_title="title"
        )

        #then
        self.assertEqual(response, True)
        blocklist.document.assert_called_with("1")
        doc.set.assert_called_with({"title":"title"})

    def test_add_to_blocklist_should_get_title_if_it_is_cached(self):
        #given
        db = MagicMock(firestore.Client)
        doc = MagicMock(firestore.DocumentReference)
        doc.set = MagicMock(return_value="success")
        blocklist = MagicMock(firestore.CollectionReference)
        blocklist.document = MagicMock(return_value=doc)
        under_test = M2wMovieHandler(db=db)
        get_one_doc = MagicMock(firestore.DocumentSnapshot)
        under_test.get_one = MagicMock(return_value=get_one_doc)
        get_one_doc.to_dict = MagicMock(return_value={"title":"cached"})

        #when
        response = under_test.add_to_blocklist(
            movie_id="1",
            blocklist=blocklist
        )

        #then
        self.assertEqual(response, True)
        blocklist.document.assert_called_with("1")
        doc.set.assert_called_with({"title":"cached"})
        under_test.get_one.assert_called_with(id_="1")

class TestM2wGroupHandler(TestCase):
    def test_get_all_group_members_should_return_stream(self):
        #given
        db = MagicMock(firestore.Client)
        under_test = M2wGroupHandler(db=db)
        group = MagicMock(firestore.DocumentSnapshot)
        group_ref = MagicMock(firestore.DocumentReference)
        group.reference = group_ref
        members = MagicMock(firestore.CollectionReference)
        members.stream = MagicMock(return_value=range(3))
        group_ref.collection = members
        under_test.get_one = MagicMock(return_value=group)

        #when
        response = under_test.get_all_group_members("group_1")

        #then
        for r in response:
            self.assertIn(r, [0,1,2])
        under_test.get_one.assert_called_with(id_="group_1")
        group_ref.collection.assert_called_with("members")

    def test_get_all_group_members_should_raise_exception_if_group_is_missing(self):
        #given
        db = MagicMock(firestore.Client)
        under_test = M2wGroupHandler(db=db)
        def raise_exception(*args, **kwargs):
            raise M2WDatabaseException()
        under_test.get_one = MagicMock(side_effect=raise_exception)

        #when
        with self.assertRaises(M2WDatabaseException) as context:
            under_test.get_all_group_members("group_1")

        #then
        self.assertIsInstance(context.exception, M2WDatabaseException)
        under_test.get_one.assert_called_with(id_="group_1")

    def test_add_member_to_group_should_return_dict(self):
        #given
        db = MagicMock(firestore.Client)
        under_test = M2wGroupHandler(db=db)
        group = MagicMock(firestore.DocumentSnapshot)
        group_ref = MagicMock(firestore.DocumentReference)
        members_coll = MagicMock(firestore.CollectionReference)
        doc = MagicMock(firestore.DocumentReference)
        new_user = MagicMock(firestore.DocumentSnapshot)
        new_user.id = "user1"
        new_user.to_dict = MagicMock(return_value={
            'email': 'x.y@mail.com'
        })
        doc.set = MagicMock(return_value={'success':True})
        members_coll.document = MagicMock(return_value=doc)
        group_ref.collection = MagicMock(return_value=members_coll)
        group.reference = group_ref
        under_test.get_one = MagicMock(return_value=group)

        #when
        response = under_test.add_member_to_group(
            group_id="group1",
            user = new_user
        )

        #then
        self.assertEqual(response, {"success": True, "message": "OK"})
        under_test.get_one.assert_called_with(id_="group1")
        group_ref.collection.assert_called_with('members')
        members_coll.document.assert_called_with("user1")
        doc.set.assert_called_with({'email': 'x.y@mail.com'})

    def test_add_member_to_group_should_return_as_unsuccessful_if_group_does_not_exist(self):
        #given
        db = MagicMock(firestore.Client)
        under_test = M2wGroupHandler(db=db)
        new_user = MagicMock(firestore.DocumentSnapshot)
        new_user.id = "user1"
        new_user.to_dict = MagicMock(return_value={
            'email': 'x.y@mail.com'
        })
        def raise_exception():
            raise M2WDatabaseException("No group.")
        under_test.get_one = MagicMock(side_effect=raise_exception)

        #when
        response = under_test.add_member_to_group(
            group_id="group1",
            user = new_user
        )

        #then
        self.assertEqual(response['success'], False)
        under_test.get_one.assert_called_with(id_="group1")

    def test_remove_member_from_group_should_return_dict(self):
        #given
        db = MagicMock(firestore.Client)
        under_test = M2wGroupHandler(db=db)
        group = MagicMock(firestore.DocumentSnapshot)
        group_ref = MagicMock(firestore.DocumentReference)
        members_coll = MagicMock(firestore.CollectionReference)
        doc = MagicMock(firestore.DocumentReference)
        doc.delete = MagicMock(return_value={'success':True})
        members_coll.document = MagicMock(return_value=doc)
        group_ref.collection = MagicMock(return_value=members_coll)
        group.reference = group_ref
        under_test.get_one = MagicMock(return_value=group)

        #when
        response = under_test.remove_member_from_group(
            group_id="group1",
            user_id="user1"
        )

        #then
        self.assertEqual(response, {"success": True, "message": "OK"})
        under_test.get_one.assert_called_with(id_="group1")
        group_ref.collection.assert_called_with('members')
        members_coll.document.assert_called_with("user1")

    def test_remove_member_from_group_should_return_as_unsuccessful_if_group_does_not_exist(self):
        #given
        db = MagicMock(firestore.Client)
        under_test = M2wGroupHandler(db=db)
        def raise_exception():
            raise M2WDatabaseException("No group.")
        under_test.get_one = MagicMock(side_effect=raise_exception)

        #when
        response = under_test.remove_member_from_group(
            group_id="group1",
            user_id="user1"
        )

        #then
        self.assertEqual(response['success'], False)
        under_test.get_one.assert_called_with(id_="group1")

    def test_create_new_should_return_dict(self):
        #given
        db = MagicMock(firestore.Client)
        collection_ref = MagicMock(firestore.CollectionReference)
        group_ref = MagicMock(firestore.DocumentReference)
        group_ref.id = "new_group"
        collection_ref.add = MagicMock(return_value=("timestamp", group_ref))
        db.collection = MagicMock(return_value=collection_ref)
        member1 = MagicMock(firestore.DocumentSnapshot)
        member2 = MagicMock(firestore.DocumentSnapshot)
        under_test = M2wGroupHandler(db=db)
        under_test.add_member_to_group = MagicMock(return_value={
            "success": True,
            "message": "OK"
        })

        #when
        response = under_test.create_new(
            data={
                "locale": "HU",
                "name": "My Group"
            },
            members=[member1, member2]
        )

        #then
        self.assertEqual(response, {
                "success": True,
                "group_reference": group_ref,
                "added_members": [member1, member2],
                "number_of_new_members": 2
            })
        db.collection.assert_called_with("groups")
        collection_ref.add.assert_called_with(document_data={
                "locale": "HU",
                "name": "My Group"
            })
        under_test.add_member_to_group.assert_called_with(group_id="new_group", user=member2)

    def test_create_new_should_raise_exception_if_group_not_created(self):
        #given
        db = MagicMock(firestore.Client)
        def raise_exception():
            raise M2WDatabaseException("No group.")
        db.collection = MagicMock(side_effect=raise_exception)
        member = MagicMock(firestore.DocumentSnapshot)
        under_test = M2wGroupHandler(db=db)

        #when
        with self.assertRaises(M2WDatabaseException) as context:
            under_test.create_new(
                data={
                    "locale": "HU",
                    "name": "My Group"
                },
                members=member
            )

        #then
        self.assertIsInstance(context.exception, M2WDatabaseException)        
        db.collection.assert_called_with("groups")

    def test_create_new_should_raise_exception_if_group_created_but_could_not_add_members(self):
        #given
        db = MagicMock(firestore.Client)
        collection_ref = MagicMock(firestore.CollectionReference)
        group_ref = MagicMock(firestore.DocumentReference)
        group_ref.id = "new_group"
        collection_ref.add = MagicMock(return_value=("timestamp", group_ref))
        db.collection = MagicMock(return_value=collection_ref)
        member1 = MagicMock(firestore.DocumentSnapshot)
        member2 = MagicMock(firestore.DocumentSnapshot)
        under_test = M2wGroupHandler(db=db)
        under_test.add_member_to_group = MagicMock(return_value={
            "success": False,
            "message": "Exception"
        })

        #when
        with self.assertRaises(M2WDatabaseException) as context:
            under_test.create_new(
                data={
                    "locale": "HU",
                    "name": "My Group"
                },
                members=[member1, member2]
            )

        #then
        self.assertIsInstance(context.exception, M2WDatabaseException)
        db.collection.assert_called_with("groups")
        collection_ref.add.assert_called_with(document_data={
                "locale": "HU",
                "name": "My Group"
            })
        under_test.add_member_to_group.assert_called_with(group_id="new_group", user=member2)
