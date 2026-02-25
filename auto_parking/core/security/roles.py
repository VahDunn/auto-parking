from fastapi import Depends, HTTPException, status

from auto_parking.core.security.actor import Actor, get_current_actor

get_current_actor_dep = Depends(get_current_actor)


def require_admin(actor: Actor = get_current_actor_dep) -> Actor:
    if actor.type != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return actor


def require_manager(actor: Actor = get_current_actor_dep) -> Actor:
    if actor.type != "manager":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager only")
    return actor
