from auto_parking.db.models import Driver, Notification, OutboxEvent, user_enterprise
from auto_parking.db.models.vehicle_to_driver import VehicleDriverAssignment


def _indexes_by_name(table):
    return {
        index.name: [column.name for column in index.columns]
        for index in table.indexes
    }


def test_vehicle_driver_assignment_has_reverse_lookup_index():
    indexes = _indexes_by_name(VehicleDriverAssignment.__table__)

    assert indexes["ix_vehicle_driver_assignment_driver_vehicle"] == [
        "driver_id",
        "vehicle_id",
    ]


def test_driver_has_enterprise_lookup_index():
    indexes = _indexes_by_name(Driver.__table__)

    assert indexes["ix_driver_enterprise_id"] == ["enterprise_id"]


def test_user_enterprise_has_reverse_lookup_index():
    indexes = _indexes_by_name(user_enterprise)

    assert indexes["ix_user_enterprise_enterprise_user"] == [
        "enterprise_id",
        "user_id",
    ]


def test_notification_has_hot_list_indexes():
    indexes = _indexes_by_name(Notification.__table__)

    assert indexes["ix_notification_recipient_created_id"] == [
        "recipient_user_id",
        "created_at",
        "id",
    ]
    assert indexes["ix_notification_unread_recipient_created_id"] == [
        "recipient_user_id",
        "created_at",
        "id",
    ]


def test_outbox_event_has_pending_dispatch_index():
    indexes = _indexes_by_name(OutboxEvent.__table__)

    assert indexes["ix_outbox_event_pending_next_attempt_id"] == [
        "next_attempt_at",
        "id",
    ]
