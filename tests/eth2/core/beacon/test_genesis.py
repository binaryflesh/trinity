from eth.constants import ZERO_HASH32
import pytest

from eth2.beacon.constants import GENESIS_EPOCH, GENESIS_SLOT, JUSTIFICATION_BITS_LENGTH
from eth2.beacon.genesis import (
    _genesis_time_from_eth1_timestamp,
    get_genesis_block,
    initialize_beacon_state_from_eth1,
)
from eth2.beacon.tools.builder.initializer import create_mock_deposits_and_root
from eth2.beacon.types.block_headers import BeaconBlockHeader
from eth2.beacon.types.blocks import BeaconBlock, BeaconBlockBody
from eth2.beacon.types.eth1_data import Eth1Data
from eth2.beacon.types.forks import Fork
from eth2.beacon.typing import Gwei


def test_get_genesis_block():
    genesis_state_root = b"\x10" * 32
    genesis_slot = 0
    genesis_block = get_genesis_block(genesis_state_root, BeaconBlock)
    assert genesis_block.slot == genesis_slot
    assert genesis_block.parent_root == ZERO_HASH32
    assert genesis_block.state_root == genesis_state_root
    assert genesis_block.body.is_empty


@pytest.mark.parametrize(("validator_count,"), [(10)])
def test_get_genesis_beacon_state(
    validator_count,
    pubkeys,
    max_committees_per_slot,
    slots_per_historical_root,
    epochs_per_slashings_vector,
    epochs_per_historical_vector,
    genesis_delay,
    config,
    keymap,
):
    genesis_deposits, deposit_root = create_mock_deposits_and_root(
        pubkeys=pubkeys[:validator_count], keymap=keymap, config=config
    )

    genesis_eth1_data = Eth1Data.create(
        deposit_count=len(genesis_deposits),
        deposit_root=deposit_root,
        block_hash=ZERO_HASH32,
    )
    eth1_timestamp = 10
    eth1_block_hash = genesis_eth1_data.block_hash

    state = initialize_beacon_state_from_eth1(
        eth1_block_hash=eth1_block_hash,
        eth1_timestamp=eth1_timestamp,
        deposits=genesis_deposits,
        config=config,
    )

    # Versioning
    assert state.slot == GENESIS_SLOT
    assert state.genesis_time == _genesis_time_from_eth1_timestamp(
        eth1_timestamp, genesis_delay
    )
    assert state.fork == Fork.create()

    # History
    assert state.latest_block_header == BeaconBlockHeader.create(
        body_root=BeaconBlockBody.create().hash_tree_root
    )
    assert len(state.block_roots) == slots_per_historical_root
    assert tuple(state.block_roots) == (ZERO_HASH32,) * slots_per_historical_root
    assert len(state.state_roots) == slots_per_historical_root
    assert tuple(state.block_roots) == (ZERO_HASH32,) * slots_per_historical_root
    assert len(state.historical_roots) == 0

    # Ethereum 1.0 chain data
    assert state.eth1_data == genesis_eth1_data
    assert len(state.eth1_data_votes) == 0
    assert state.eth1_deposit_index == len(genesis_deposits)

    # Validator registry
    assert len(state.validators) == validator_count
    assert len(state.balances) == validator_count

    # Shuffling
    assert len(state.randao_mixes) == epochs_per_historical_vector
    assert (
        tuple(state.randao_mixes) == (eth1_block_hash,) * epochs_per_historical_vector
    )

    # Slashings
    assert len(state.slashings) == epochs_per_slashings_vector
    assert tuple(state.slashings) == (Gwei(0),) * epochs_per_slashings_vector

    # Attestations
    assert len(state.previous_epoch_attestations) == 0
    assert len(state.current_epoch_attestations) == 0

    # Justification
    assert state.previous_justified_checkpoint.epoch == GENESIS_EPOCH
    assert state.previous_justified_checkpoint.root == ZERO_HASH32
    assert state.current_justified_checkpoint.epoch == GENESIS_EPOCH
    assert state.current_justified_checkpoint.root == ZERO_HASH32
    assert state.justification_bits == (False,) * JUSTIFICATION_BITS_LENGTH

    # Finalization
    assert state.finalized_checkpoint.epoch == GENESIS_EPOCH
    assert state.finalized_checkpoint.root == ZERO_HASH32

    for i in range(len(genesis_deposits)):
        assert state.validators[i].is_active(GENESIS_EPOCH)
