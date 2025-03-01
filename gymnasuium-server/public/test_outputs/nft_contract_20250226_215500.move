module 0x0::my_module {

    // Import modules for UID generation, signing, and transaction context.
    use sui::object::{self, UID};
    use sui::tx_context::TxContext;
    use std::signer;

    ////////////////////////////////////////////////////////////////////////////
    // DATA STRUCTURES
    ////////////////////////////////////////////////////////////////////////////

    // Metadata struct to hold NFT metadata.
    // Using vector<u8> for string data to remain generic and efficient.
    struct Metadata has copy, drop, store {
        name: vector<u8>,
        description: vector<u8>,
        image_url: vector<u8>,
    }

    // NFT resource representing a unique token.
    // The 'key' ability enables this resource to have a unique ID,
    // while 'store' allows the object to be stored on-chain.
    struct NFT has key, store {
        id: UID,
        metadata: Metadata,
        // The 'owner' field tracks the current owner of the NFT.
        owner: address,
    }

    // MinterCap resource for access control.
    // Only accounts holding a MinterCap can mint new NFTs.
    struct MinterCap has key, store {}

    ////////////////////////////////////////////////////////////////////////////
    // INITIALIZATION FUNCTION
    ////////////////////////////////////////////////////////////////////////////

    // init_module publishes a MinterCap resource into the caller's account.
    // This function should be called once by the contract administrator.
    public fun init_module(account: &signer) {
        // Only publish a MinterCap if one is not already present.
        if (!exists<MinterCap>(signer::address_of(account))) {
            move_to(account, MinterCap {});
        }
    }

    ////////////////////////////////////////////////////////////////////////////
    // MINTING FUNCTIONALITY
    ////////////////////////////////////////////////////////////////////////////

    // mint_nft allows minting of a new NFT.
    // Only accounts holding a MinterCap (hence authorized) can call this function.
    // The newly minted NFT is automatically deposited in the minter's account.
    public fun mint_nft(
        minter: &signer,
        ctx: &mut TxContext,
        name: vector<u8>,
        description: vector<u8>,
        image_url: vector<u8>
    ) {
        // Verify that the caller has the minting capability.
        assert!(exists<MinterCap>(signer::address_of(minter)), 100);

        // Generate a new unique identifier for the NFT.
        let new_uid = object::new_uid(ctx);

        // Construct the metadata for the NFT.
        let metadata = Metadata { name, description, image_url };

        // Create the NFT with the owner set to the minter's address.
        let nft = NFT { id: new_uid, metadata, owner: signer::address_of(minter) };

        // Deposit the NFT into the minter's account.
        move_to(minter, nft);
    }

    ////////////////////////////////////////////////////////////////////////////
    // TRANSFER FUNCTIONALITY
    ////////////////////////////////////////////////////////////////////////////

    // transfer_nft transfers an NFT from its current owner to a new owner.
    // This function takes ownership of the NFT resource from the caller and
    // returns an updated NFT with its owner field changed to the recipient.
    public fun transfer_nft(
        owner: &signer,
        nft: NFT,
        recipient: address
    ) : NFT {
        // Ensure that only the owner can transfer the NFT.
        assert!(nft.owner == signer::address_of(owner), 101);

        // Update the NFT's owner to the recipient.
        let new_nft = NFT { id: nft.id, metadata: nft.metadata, owner: recipient };

        // Return the updated NFT.
        new_nft
    }

    ////////////////////////////////////////////////////////////////////////////
    // UPDATE METADATA FUNCTIONALITY
    ////////////////////////////////////////////////////////////////////////////

    // update_metadata allows the owner of an NFT to update its metadata.
    // The function checks that the caller is the NFT's owner and then returns
    // an updated NFT with new metadata.
    public fun update_metadata(
        owner: &signer,
        nft: NFT,
        new_name: vector<u8>,
        new_description: vector<u8>,
        new_image_url: vector<u8>
    ) : NFT {
        // Ensure that only the owner can update the metadata.
        assert!(nft.owner == signer::address_of(owner), 102);

        // Construct the updated metadata.
        let new_metadata = Metadata { name: new_name, description: new_description, image_url: new_image_url };

        // Create an updated NFT with the new metadata.
        let updated_nft = NFT { id: nft.id, metadata: new_metadata, owner: nft.owner };

        // Return the updated NFT.
        updated_nft
    }
}