from career_assistant.database import DATA_SOURCE_NOTE


def test_database_discloses_demo_data_source():
    assert "学校官方公开报告" in DATA_SOURCE_NOTE
    assert "社会平均工资" in DATA_SOURCE_NOTE
    assert "学校官方薪资" in DATA_SOURCE_NOTE
