from eth_utils import ValidationError
import pytest

from eth2._utils.bls import bls
from eth2.beacon.helpers import (
    compute_signing_root,
    compute_start_slot_at_epoch,
    get_domain,
)
from eth2.beacon.signature_domain import SignatureDomain
from eth2.beacon.state_machines.forks.serenity.block_validation import (
    validate_block_slot,
    validate_proposer_signature,
    validate_randao_reveal,
)
from eth2.beacon.tools.builder.initializer import create_mock_validator
from eth2.beacon.types.blocks import BeaconBlock, SignedBeaconBlock
from eth2.beacon.types.states import BeaconState
from eth2.beacon.typing import SerializableUint64


@pytest.mark.parametrize(
    "state_slot," "block_slot," "expected",
    ((10, 10, None), (1, 10, ValidationError()), (10, 1, ValidationError())),
)
def test_validate_block_slot(
    sample_beacon_state_params,
    sample_beacon_block_params,
    state_slot,
    block_slot,
    expected,
):
    state = BeaconState.create(**sample_beacon_state_params).set("slot", state_slot)
    block = BeaconBlock.create(**sample_beacon_block_params).set("slot", block_slot)
    if isinstance(expected, Exception):
        with pytest.raises(ValidationError):
            validate_block_slot(state, block)
    else:
        validate_block_slot(state, block)


@pytest.mark.parametrize(
    "slots_per_epoch, max_committees_per_slot,"
    "proposer_privkey, proposer_pubkey, is_valid_signature",
    (
        (5, 5, 56, bls.sk_to_pk(56), True),
        (5, 5, 56, bls.sk_to_pk(56)[1:] + b"\x01", False),
        (5, 5, 123, bls.sk_to_pk(123), True),
        (5, 5, 123, bls.sk_to_pk(123)[1:] + b"\x01", False),
    ),
)
def test_validate_proposer_signature(
    slots_per_epoch,
    max_committees_per_slot,
    proposer_privkey,
    proposer_pubkey,
    is_valid_signature,
    sample_beacon_block_params,
    sample_beacon_state_params,
    target_committee_size,
    max_effective_balance,
    config,
):

    state = BeaconState.create(**sample_beacon_state_params).mset(
        "validators",
        tuple(create_mock_validator(proposer_pubkey, config) for _ in range(10)),
        "balances",
        (max_effective_balance,) * 10,
    )

    block = BeaconBlock.create(**sample_beacon_block_params)
    domain = get_domain(state, SignatureDomain.DOMAIN_BEACON_PROPOSER, slots_per_epoch)
    signing_root = compute_signing_root(block, domain)

    proposed_block = SignedBeaconBlock.create(
        message=block, signature=bls.sign(proposer_privkey, signing_root)
    )

    if is_valid_signature:
        validate_proposer_signature(state, proposed_block, config)
    else:
        with pytest.raises(ValidationError):
            validate_proposer_signature(state, proposed_block, config)


@pytest.mark.parametrize(
    [
        "is_valid",
        "epoch",
        "expected_epoch",
        "proposer_key_index",
        "expected_proposer_key_index",
    ],
    ((True, 0, 0, 0, 0), (True, 1, 1, 1, 1), (False, 0, 1, 0, 0), (False, 0, 0, 0, 1)),
)
def test_randao_reveal_validation(
    is_valid,
    epoch,
    expected_epoch,
    proposer_key_index,
    expected_proposer_key_index,
    privkeys,
    pubkeys,
    sample_fork_params,
    genesis_state,
    config,
):
    state = genesis_state.set(
        "slot", compute_start_slot_at_epoch(epoch, config.SLOTS_PER_EPOCH)
    )
    slots_per_epoch = config.SLOTS_PER_EPOCH
    domain = get_domain(state, SignatureDomain.DOMAIN_RANDAO, slots_per_epoch)
    signing_root = compute_signing_root(SerializableUint64(epoch), domain)

    proposer_privkey = privkeys[proposer_key_index]
    randao_reveal = bls.sign(proposer_privkey, signing_root)

    try:
        validate_randao_reveal(
            state=state,
            proposer_index=expected_proposer_key_index,
            epoch=expected_epoch,
            randao_reveal=randao_reveal,
            slots_per_epoch=slots_per_epoch,
        )
    except ValidationError:
        if is_valid:
            raise
    else:
        if not is_valid:
            pytest.fail("Did not raise")
