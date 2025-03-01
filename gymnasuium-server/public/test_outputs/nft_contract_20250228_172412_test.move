// File: my_module_tests.move
// This test file is intended to be run with the Sui Move test framework.
// It provides a fake transaction context (TestTxContext) that mimics the minimal
// behavior of sui::tx_context::TxContext so that we can test my_module functions.
// IMPORTANT: In an actual Sui environment, the real TxContext is provided by the framework.
// The TestTxContext here is for unit testing only.

module 0x0::my_module_tests {
    use 0x0::my_module;
    use sui::object::UID;

    ////////////////////////////////////////////////////////////////////////////
    // Test Transaction Context
    ////////////////////////////////////////////////////////////////////////////

    // TestTxContext is a fake transaction context for testing purposes.
    // It provides a sender() function and a fresh_id() function that returns a deterministic UID.
    struct TestTxContext has store, drop {
        sender: address,
        counter: u64,
    }

    // Creates a new TestTxContext with the given sender address.
    public fun new_test_tx_context(sender: address): TestTxContext {
        TestTxContext { sender, counter: 0 }
    }

    // Returns a fresh UID based on an internal counter.
    // This function mimics sui::tx_context::TxContext::fresh_id.
    public fun fresh_id(ctx: &mut TestTxContext): UID {
        let curr = ctx.counter;
        ctx.counter = curr + 1;
        // Construct a UID. Here we assume UID is a struct with a single field `id: u64`.
        UID { id: curr }
    }

    // Returns the sender address from the context.
    // This function mimics the method call ctx.sender() in sui::tx_context::TxContext.
    public fun get_sender(ctx: &TestTxContext): address {
        ctx.sender
    }

    // We provide a shim that forwards calls from sui::tx_context::TxContext to TestTxContext.
    // To enable this, we shadow the functions expected in the my_module test context.
    public fun tx_fresh_id(ctx: &mut TestTxContext): UID {
        fresh_id(ctx)
    }
    public fun tx_sender(ctx: &TestTxContext): address {
        get_sender(ctx)
    }

    //////////////////////////////////////////////////////////////////////////////
    // Overriding functions for testing:
    //
    // In the my_module contract, functions call:
    //   TxContext::fresh_id(ctx)
    //   ctx.sender()
    // Since our TestTxContext is used in tests, we create local wrapper functions that
    // simulate these calls. We then override these calls in our tests by shadowing them
    // with the ones provided above.
    //
    // IMPORTANT: In a real Sui test environment, the actual TxContext would be provided
    // by the framework, so this shim is only for unit testing.
    //////////////////////////////////////////////////////////////////////////////

    // We now use the following functions to simulate the TxContext calls in our tests.
    // To connect with my_module, we rely on the fact that the logic of my_module is agnostic
    // to the specific implementation of TxContext, so we manually inject our TestTxContext.
    //
    // NOTE: For the purposes of these tests, we assume that the functions in my_module that call
    // TxContext::fresh_id and ctx.sender() get linked with our local implementations below.
    //
    // To achieve this in testing, you may need to configure the test framework to use the TestTxContext.
    // For this example, we assume that our TestTxContext is accepted by my_module functions.

    ////////////////////////////////////////////////////////////////////////////
    // Tests
    ////////////////////////////////////////////////////////////////////////////

    // Test for creating a minting capability.
    // Checks that the admin field is correctly set to the transaction sender.
    #[test]
    public fun test_create_mint_cap() {
        let sender = @0x1;
        let mut ctx = new_test_tx_context(sender);
        // Call create_mint_cap from my_module.
        let mint_cap = my_module::create_mint_cap(&mut ctx);
        // Verify that the admin matches the sender.
        assert!(mint_cap.admin == sender, 1);
    }

    // Test minting an NFT with proper admin authorization (happy path).
    #[test]
    public fun test_mint_nft_happy_path() {
        let admin = @0x2;
        let recipient = @0x3;
        let mut ctx = new_test_tx_context(admin);
        let mint_cap = my_module::create_mint_cap(&mut ctx);
        let name = b"My NFT";              // vector<u8>
        let description = b"An awesome NFT"; // vector<u8>
        let image_url = b"http://example.com/image.png"; // vector<u8>
        // Mint the NFT.
        let (nft, returned_cap) = my_module::mint_nft(
            mint_cap,
            recipient,
            name,
            description,
            image_url,
            &mut ctx
        );
        // Verify that the NFT owner is the intended recipient.
        assert!(nft.owner == recipient, 2);
        // Verify that the minting capability remains unchanged.
        assert!(returned_cap.admin == admin, 3);
    }

    // Test unauthorized NFT minting.
    // The sender is not the admin in the mint_cap, so the function should abort with code 100.
    #[test(should_abort = 100)]
    public fun test_mint_nft_unauthorized() {
        let admin = @0x4;
        let non_admin = @0x5;
        let recipient = @0x6;
        // Create a context with admin privileges and create the mint cap.
        let mut ctx = new_test_tx_context(admin);
        let mint_cap = my_module::create_mint_cap(&mut ctx);
        // Change the context sender to a non-admin address.
        ctx.sender = non_admin;
        let name = b"Unauthorized NFT";
        let description = b"Should not be minted";
        let image_url = b"http://example.com/unauthorized.png";
        // This call should abort because non_admin is not authorized to mint.
        my_module::mint_nft(
            mint_cap,
            recipient,
            name,
            description,
            image_url,
            &mut ctx
        );
    }

    // Test NFT transfer by the rightful owner (happy path).
    #[test]
    public fun test_transfer_nft_happy_path() {
        let owner = @0x7;
        let new_owner = @0x8;
        let mut ctx = new_test_tx_context(owner);
        // Create a mint capability and mint an NFT owned by the sender.
        let mint_cap = my_module::create_mint_cap(&mut ctx);
        let name = b"Transferable NFT";
        let description = b"NFT to be transferred";
        let image_url = b"http://example.com/transfer.png";
        let (nft, _) = my_module::mint_nft(
            mint_cap,
            owner,
            name,
            description,
            image_url,
            &mut ctx
        );
        // Transfer the NFT to a new owner.
        let transferred_nft = my_module::transfer_nft(nft, new_owner, &mut ctx);
        // Verify that the NFT owner has been updated.
        assert!(transferred_nft.owner == new_owner, 4);
    }

    // Test unauthorized NFT transfer.
    // A non-owner attempts to transfer the NFT, which should abort with code 101.
    #[test(should_abort = 101)]
    public fun test_transfer_nft_unauthorized() {
        let owner = @0x9;
        let malicious = @0xA;
        let new_owner = @0xB;
        let mut ctx = new_test_tx_context(owner);
        // Mint an NFT.
        let mint_cap = my_module::create_mint_cap(&mut ctx);
        let name = b"Stolen NFT";
        let description = b"NFT that will be stolen";
        let image_url = b"http://example.com/stolen.png";
        let (nft, _) = my_module::mint_nft(
            mint_cap,
            owner,
            name,
            description,
            image_url,
            &mut ctx
        );
        // Change the context sender to a malicious address.
        ctx.sender = malicious;
        // Attempt an unauthorized transfer.
        my_module::transfer_nft(nft, new_owner, &mut ctx);
    }

    // Test NFT metadata update by the owner (happy path).
    #[test]
    public fun test_update_nft_metadata_happy_path() {
        let owner = @0xC;
        let mut ctx = new_test_tx_context(owner);
        // Mint an NFT owned by the sender.
        let mint_cap = my_module::create_mint_cap(&mut ctx);
        let name = b"Old NFT";
        let description = b"Old description";
        let image_url = b"http://example.com/old.png";
        let (nft, _) = my_module::mint_nft(
            mint_cap,
            owner,
            name,
            description,
            image_url,
            &mut ctx
        );
        // New metadata to update.
        let new_name = b"New NFT";
        let new_description = b"New description";
        let new_image_url = b"http://example.com/new.png";
        // Update the NFT metadata.
        let updated_nft = my_module::update_nft_metadata(nft, new_name, new_description, new_image_url, &mut ctx);
        // Verify that the metadata has been updated.
        assert!(updated_nft.name == new_name, 5);
        assert!(updated_nft.description == new_description, 6);
        assert!(updated_nft.image_url == new_image_url, 7);
    }

    // Test unauthorized NFT metadata update.
    // A non-owner attempts to update the metadata, which should abort with code 102.
    #[test(should_abort = 102)]
    public fun test_update_nft_metadata_unauthorized() {
        let owner = @0xD;
        let attacker = @0xE;
        let mut ctx = new_test_tx_context(owner);
        // Mint an NFT.
        let mint_cap = my_module::create_mint_cap(&mut ctx);
        let name = b"Immutable NFT";
        let description = b"Cannot be updated by others";
        let image_url = b"http://example.com/immutable.png";
        let (nft, _) = my_module::mint_nft(
            mint_cap,
            owner,
            name,
            description,
            image_url,
            &mut ctx
        );
        // Change the context sender to an attacker.
        ctx.sender = attacker;
        let new_name = b"Fake NFT";
        let new_description = b"Fake update";
        let new_image_url = b"http://example.com/fake.png";
        // Attempt an unauthorized metadata update.
        my_module::update_nft_metadata(nft, new_name, new_description, new_image_url, &mut ctx);
    }
}