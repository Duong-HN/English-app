from app.models import LearningSpace, User, VocabularyItem


def test_learning_space_has_database_enforced_self_uniqueness():
    index = next(
        index for index in LearningSpace.__table__.indexes if index.name == "uq_learning_space_user_self"
    )

    assert index.unique is True
    assert "user_id" in {column.name for column in index.columns}


def test_vocabulary_word_is_normalized_when_assigned(db_session):
    user = User(email="normalized-word@example.com", display_name="Normalized Word")
    db_session.add(user)
    db_session.flush()

    item = VocabularyItem(
        user_id=user.id,
        word="  English   ",
        meaning="ngôn ngữ Anh",
    )
    db_session.add(item)
    db_session.flush()

    assert item.word == "English"
    assert item.word_normalized == "english"
