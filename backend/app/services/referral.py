from sqlalchemy.orm import Session

from app.models.referral import Referral


def apply_referral_commission(db: Session, inviter_id: int, invitee_id: int, amount_rub: int) -> int:
    referral = (
        db.query(Referral)
        .filter(Referral.inviter_id == inviter_id, Referral.invitee_id == invitee_id)
        .first()
    )
    if not referral:
        return 0

    commission = int(amount_rub * referral.commission_percent / 100)
    referral.total_earned_rub += commission
    db.commit()
    return commission
