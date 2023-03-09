CKEDITOR.plugins.add( 'custom_complete', {
	requires: 'autocomplete,textmatch',

	init: function( editor ) {
		editor.on( 'instanceReady', function() {
			let config = {};
			// Called when the user types in the editor or moves the caret.
			// The range represents the caret position.
			function textTestCallback( range ) {
				// You do not want to autocomplete a non-empty selection.
				if ( !range.collapsed ) {
					return null;
				}

				// Use the text match plugin which does the tricky job of performing
				// a text search in the DOM. The "matchCallback" function should return
				// a matching fragment of the text.
				return CKEDITOR.plugins.textMatch.match( range, matchCallback );
			}

			// Returns the position of the matching text.
			// It matches a word starting from the '#' character
			// up to the caret position.
			function matchCallback( text, offset ) {
				// Get the text before the caret.
				let left = text.slice( 0, offset ),
					// Will look for a '#' character followed by a ticket number.
					match = left.match( /{$/ );

				if ( !match ) {
					return null;
				}
				return {
					start: match.index,
					end: offset
				};
			}

			config.textTestCallback = textTestCallback;
//		   The itemsArray variable is the example
//			let itemsArray = [
//				{
//				    id: 0,
//					name: 'Имя',
//					tag: '{{ name }}'
//				},
//			];

            // Need put json in auto_complete_items variable

			// Returns (through its callback) the suggestions for the current query.
			function dataCallback( matchInfo, callback ) {
				// Remove the '#' tag.
				let query = matchInfo.query.substring( 1 );
				let itemsArray
				if (typeof(custom_complete_items) != 'undefined'){
                        itemsArray = custom_complete_items
                    } else {
                        itemsArray = []
                    }
				// Simple search.
				// Filter the entire items array so only the items that start
				// with the query remain.
				let suggestions = itemsArray.filter( function( item ) {
					return String( item.id ).indexOf( query ) == 0;
				} );

				// Note: The callback function can also be executed asynchronously
				// so dataCallback can do an XHR request or use any other asynchronous API.
				callback( suggestions );
			}

		    config.dataCallback = dataCallback;


			// Define the templates of the autocomplete suggestions dropdown and output text.
			config.itemTemplate = '<li data-id="{id}">#{id}: {name}</li>';
			config.outputTemplate = '{tag}'
			// Attach autocomplete to the editor.
            editor.addCommand('reload_autocomplete', {
               exec: function(edt) {
                   CKEDITOR.plugins.autocomplete = new CKEDITOR.plugins.autocomplete(editor, config)
               }
            })
            new CKEDITOR.plugins.autocomplete(editor, config)

		});
	}
} );