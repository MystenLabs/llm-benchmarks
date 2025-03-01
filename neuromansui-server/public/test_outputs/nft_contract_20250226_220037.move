module temp_addr::my_module {

    // Import necessary Sui modules.
    use sui::object::{UID, new};
    use sui::tx_context::TxContext;

    // NFTAdmin struct acts as an admin for minting NFTs.
    // It includes a unique identifier and the admin owner's address.
    // The 'drop' ability is added so that objects of this type can be returned
    // from entry functions.
    public struct NFTAdmin has key, store, drop {
        id: UID,
        owner: address,
    }

    // NFT struct representing a non-fungible token with metadata.
    // It includes a unique identifier, the owner address, and metadata fields.
    public struct NFT has key, store, drop {
        id: UID,             // Unique identifier for the NFT.
        owner: address,      // Current owner of the NFT.
        name: vector<u8>,    // Name metadata.
        description: vector<u8>,  // Description metadata.
        image_url: vector<u8>, // URL to the NFT image.
    }

    // The create_admin function creates an NFTAdmin object.
    // Only the account with the provided owner address will have admin powers.
    public entry fun create_admin(owner: address, ctx: &mut TxContext): NFTAdmin {
        // Generate a new unique identifier using the Sui framework's helper.
        let new_id = new(ctx);
        NFTAdmin { id: new_id, owner }
    }

    // The mint function allows an admin to mint a new NFT.
    // It takes the admin reference, transaction context, and metadata parameters.
    public entry fun mint(admin: &NFTAdmin, ctx: &mut TxContext, name: vector<u8>, description: vector<u8>, image_url: vector<u8>): NFT {
        // In a real-world scenario, you would enforce that the caller is the admin.owner.
        let new_id = new(ctx);
        NFT {
            id: new_id,
            owner: admin.owner,
            name,
            description,
            image_url,
        }
    }

    // The transfer function transfers ownership of an NFT to a new address.
    public entry fun transfer(nft: NFT, ctx: &mut TxContext, new_owner: address): NFT {
        // Destructure the NFT resource to move its fields (avoiding implicit copy of UID).
        let NFT { id, owner: old_owner, name, description, image_url } = nft;
        NFT {
            id, // The UID is moved.
            owner: new_owner,
            name,
            description,
            image_url,
        }
    }

    // The update_metadata function allows the NFT owner to change metadata.
    public entry fun update_metadata(nft: NFT, ctx: &mut TxContext, new_name: vector<u8>, new_description: vector<u8>, new_image_url: vector<u8>): NFT {
        // Destructure the NFT to move its fields.
        let NFT { id, owner, name: old_name, description: old_description, image_url: old_image_url } = nft;
        // In a production contract, you would check that the caller is the NFT owner.
        NFT {
            id,
            owner,
            name: new_name,
            description: new_description,
            image_url: new_image_url,
        }
    }
}