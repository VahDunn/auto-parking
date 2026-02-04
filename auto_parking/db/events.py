from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from auto_parking.db.models import Driver, Vehicle, VehicleDriverAssignment

_registered = False


def register_listeners() -> None:
    global _registered
    if _registered:
        return

    @event.listens_for(Session, "before_flush")
    def ensure_active_driver_in_assignment(session: Session, flush_context, instances):
        for obj in session.new.union(session.dirty):
            if not isinstance(obj, Vehicle):
                continue

            if obj.active_driver_id is None:
                continue

            active = obj.active_driver
            if active is None:
                active = session.get(Driver, obj.active_driver_id)

            if active is None:
                continue

            if active not in obj.drivers:
                obj.drivers.append(active)

    @event.listens_for(Session, "before_flush")
    def enforce_enterprise_rules(session: Session, flush_context, instances):
        for obj in session.new.union(session.dirty):
            # Правила для машин
            if isinstance(obj, Vehicle):
                state = inspect(obj)
                ad_hist = state.attrs.active_driver_id.history
                if ad_hist.has_changes():
                    new_driver_id = next(
                        (d for d in ad_hist.added if d is not None),
                        None,
                    )

                    if new_driver_id is not None:
                        active = session.get(Driver, new_driver_id)
                        if active and active.enterprise_id != obj.enterprise_id:
                            raise ValueError(
                                "Нельзя назначить активного водителя из другого предприятия."
                            )

                if state.attrs.enterprise_id.history.has_changes():
                    if obj.active_driver_id is not None:
                        raise ValueError(
                            "Нельзя менять предприятие автомобиля, пока назначен активный водитель."
                        )

            # Правила для водителей
            if isinstance(obj, Driver):
                state = inspect(obj)

                av_hist = state.attrs.active_vehicle.history

                if av_hist.has_changes() and av_hist.added:
                    new_vehicle = next(
                        (v for v in av_hist.added if v is not None),
                        None,
                    )
                    if new_vehicle is not None:
                        if new_vehicle.enterprise_id != obj.enterprise_id:
                            raise ValueError(
                                "Нельзя назначить активную машину из другого предприятия."
                            )

                if state.attrs.enterprise_id.history.has_changes():
                    vehicle = (
                        session.query(Vehicle).filter(Vehicle.active_driver_id == obj.id).first()
                    )

                    if vehicle is not None:
                        raise ValueError(
                            "Нельзя менять предприятие водителя, пока он назначен активным водителем автомобиля."
                        )

    @event.listens_for(Session, "before_flush")
    def enforce_assignment_enterprise(session: Session, flush_context, instances):
        for obj in session.new:
            if not isinstance(obj, VehicleDriverAssignment):
                continue

            vehicle = obj.vehicle or session.get(Vehicle, obj.vehicle_id)
            driver = obj.driver or session.get(Driver, obj.driver_id)

            if vehicle is None or driver is None:
                continue

            if vehicle.enterprise_id != driver.enterprise_id:
                raise ValueError("Нельзя связывать водителя и автомобиль из разных предприятий.")

    _registered = True
