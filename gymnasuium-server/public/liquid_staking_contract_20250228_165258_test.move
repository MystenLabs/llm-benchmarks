module temp_addr::my_module_test {

    use sui::object;
    use sui::tx_context;
    use sui::table;
    use sui::coin;
    use sui::signer;
    use sui::testing;

    // Import the module under test.
    use temp_addr::my_module;

    // Helper function to create a new native SUI coin for testing.
    // Assumes that coin::Coin<T> is defined with fields { id, value }.
    fun new_native_coin(value: u64, ctx: &mut tx_context::TxContext): coin::Coin<my_module::NativeSUI> {
        coin::Coin {
            id: object::new_uid(ctx),
            value,
        }
    }

    ////////////////////////////////////////////////////////////////////////////
    // Test: Initialization of StakePool.
    //
    // This test checks that initializing a new pool sets the admin and zero
    // balances as expected.
    ////////////////////////////////////////////////////////////////////////////
    #[test]
    public fun test_initialize() {
        // Create a testing context and an admin signer.
        let mut ctx = tx_context::TxContext::new_for_testing();
        let admin = testing::new_signer();

        // Initialize a new StakePool.
        let pool = my_module::initialize(&admin, &mut ctx);

        // Verify that the pool admin is correctly set.
        assert(signer::address_of(&admin) == pool.admin, 100);
        // Verify that the initial staked amount and shares are zero.
        assert(pool.total_staked == 0, 101);
        assert(pool.total_shares == 0, 102);
    }

    ////////////////////////////////////////////////////////////////////////////
    // Test: Staking native SUI.
    //
    // This test simulates a user staking native SUI coins and verifies that:
    // - The pool's total_staked and total_shares are updated correctly.
    // - LiquidStake tokens are minted and returned.
    //
    // It also tests the proportional share calculation by performing two stakes.
    ////////////////////////////////////////////////////////////////////////////
    #[test]
    public fun test_stake() {
        let mut ctx = tx_context::TxContext::new_for_testing();
        let admin = testing::new_signer();

        // Initialize pool.
        let mut pool = my_module::initialize(&admin, &mut ctx);

        // Create a test user and a coin of native SUI.
        let user = testing::new_signer();
        let stake_amount = 1000;
        let coin_native = new_native_coin(stake_amount, &mut ctx);

        // User stakes native SUI.
        let _liquid_coin = my_module::stake(&user, &mut pool, coin_native, &mut ctx);

        // After first stake, totals should equal the staked amount (1:1 mapping).
        assert(pool.total_staked == stake_amount, 200);
        assert(pool.total_shares == stake_amount, 201);

        // Stake an additional amount to test proportional share minting.
        let extra_amount = 500;
        let coin_native2 = new_native_coin(extra_amount, &mut ctx);
        let _liquid_coin2 = my_module::stake(&user, &mut pool, coin_native2, &mut ctx);

        // After second stake:
        // total_staked = 1000 + 500 = 1500.
        // Additional shares issued = (extra_amount * previous total_shares) / previous total_staked
        //                          = (500 * 1000) / 1000 = 500.
        // total_shares = 1000 + 500 = 1500.
        assert(pool.total_staked == stake_amount + extra_amount, 202);
        assert(pool.total_shares == stake_amount + 500, 203);
    }

    ////////////////////////////////////////////////////////////////////////////
    // Test: Requesting an unstake.
    //
    // This test verifies that a user can request an unstake by providing a
    // number of shares and an unlock time, and that the ticket is stored correctly.
    ////////////////////////////////////////////////////////////////////////////
    #[test]
    public fun test_request_unstake() {
        let mut ctx = tx_context::TxContext::new_for_testing();
        let admin = testing::new_signer();

        // Initialize pool.
        let mut pool = my_module::initialize(&admin, &mut ctx);

        // Create a test user.
        let user = testing::new_signer();

        // User requests to unstake.
        let unstake_shares = 300;
        let unlock_time = 1000; // arbitrary value for unlock time
        my_module::request_unstake(&user, &mut pool, unstake_shares, unlock_time, &mut ctx);

        // Retrieve the unstake ticket using the user's address.
        let ticket = table::borrow<signer::Address, my_module::StakeTicket>(
            &pool.pending_unstakes,
            signer::address_of(&user)
        );
        // Verify that the ticket details match the request.
        assert(ticket.shares == unstake_shares, 300);
        assert(ticket.unlock_time == unlock_time, 301);
    }

    ////////////////////////////////////////////////////////////////////////////
    // Test: Claiming an unstake.
    //
    // This test simulates a user staking, then requesting an unstake and finally
    // claiming the unstake. It verifies that:
    // - The correct native SUI amount is returned based on the share proportion.
    // - The pool's accounting values are updated appropriately.
    ////////////////////////////////////////////////////////////////////////////
    #[test]
    public fun test_claim_unstake() {
        let mut ctx = tx_context::TxContext::new_for_testing();
        let admin = testing::new_signer();

        // Initialize pool.
        let mut pool = my_module::initialize(&admin, &mut ctx);

        // Create a test user.
        let user = testing::new_signer();

        // User stakes native SUI.
        let stake_amount = 1200;
        let coin_native = new_native_coin(stake_amount, &mut ctx);
        let _liquid_coin = my_module::stake(&user, &mut pool, coin_native, &mut ctx);

        // User requests to unstake a portion of their shares.
        let unstake_shares = 400;
        let unlock_time = 500; // time check is ignored for this test
        my_module::request_unstake(&user, &mut pool, unstake_shares, unlock_time, &mut ctx);

        // Capture pool state prior to claiming unstake.
        let pre_total_staked = pool.total_staked;
        let pre_total_shares = pool.total_shares;

        // Expected native SUI returned = (unstake_shares * total_staked) / total_shares.
        let expected_amount = (unstake_shares * pre_total_staked) / pre_total_shares;

        // User claims the unstake.
        let native_coin_claimed = my_module::claim_unstake(&user, &mut pool, &mut ctx);

        // Verify that the minted native coin has the expected value.
        assert(coin::value(&native_coin_claimed) == expected_amount, 400);

        // Verify updated pool accounting.
        assert(pool.total_staked == pre_total_staked - expected_amount, 401);
        assert(pool.total_shares == pre_total_shares - unstake_shares, 402);
    }

    ////////////////////////////////////////////////////////////////////////////
    // Test: Delegation functionality and admin restrictions.
    //
    // This test verifies that:
    // - The admin can successfully delegate a specified amount, reducing pool's staked funds.
    // - A non-admin caller attempting to delegate triggers an abort.
    ////////////////////////////////////////////////////////////////////////////
    #[test]
    public fun test_delegate() {
        let mut ctx = tx_context::TxContext::new_for_testing();
        let admin = testing::new_signer();
        let mut pool = my_module::initialize(&admin, &mut ctx);

        // Create a test user who stakes native SUI.
        let user = testing::new_signer();
        let stake_amount = 2000;
        let coin_native = new_native_coin(stake_amount, &mut ctx);
        let _liquid_coin = my_module::stake(&user, &mut pool, coin_native, &mut ctx);

        // Admin delegates a portion of the staked SUI.
        let delegate_amount = 500;
        // Sample validator address.
        let validator: signer::Address = 0x1;
        my_module::delegate(&admin, &mut pool, validator, delegate_amount, &mut ctx);

        // Verify that the pool's total_staked is reduced accordingly.
        assert(pool.total_staked == stake_amount - delegate_amount, 500);

        // Test that a non-admin attempt to delegate aborts.
        let non_admin = testing::new_signer();
        let non_admin_delegate_amount = 100;
        // Expecting an abort with error code 1.
        testing::assert_abort(
            || { my_module::delegate(&non_admin, &mut pool, validator, non_admin_delegate_amount, &mut ctx); },
            1
        );
    }
}