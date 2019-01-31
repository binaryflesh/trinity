from eth_utils import to_tuple

from eth.constants import (
    ZERO_HASH32,
)
from eth2.beacon.constants import (
    FAR_FUTURE_SLOT,
)
from eth2.beacon.types.validator_records import (
    ValidatorRecord,
)


def mock_validator_record(pubkey,
                          withdrawal_credentials=ZERO_HASH32,
                          randao_commitment=ZERO_HASH32,
                          status_flags=0,
                          is_active=True):
    return ValidatorRecord(
        pubkey=pubkey,
        withdrawal_credentials=withdrawal_credentials,
        randao_commitment=randao_commitment,
        randao_layers=0,
        activation_slot=0 if is_active else FAR_FUTURE_SLOT,
        exit_slot=FAR_FUTURE_SLOT,
        withdrawal_slot=FAR_FUTURE_SLOT,
        penalized_slot=FAR_FUTURE_SLOT,
        exit_count=0,
        status_flags=status_flags,
        custody_commitment=b'\x55' * 32,
        latest_custody_reseed_slot=0,
        penultimate_custody_reseed_slot=0,
    )


@to_tuple
def get_pseudo_chain(length, genesis_block):
    """
    Get a pseudo chain, only slot and parent_root are valid.
    """
    block = genesis_block.copy()
    yield block
    for slot in range(1, length * 3):
        block = genesis_block.copy(
            slot=slot,
            parent_root=block.root
        )
        yield block