/*
  FILE ROLE:
  members.js handles all Members page interactions (search, Add/Edit/Delete modals, and form submit flow).

  FLOW OVERVIEW:
  Add Flow:
  1. User clicks "Add Player".
  2. JavaScript opens shared player modal in Add mode.
  3. Form submits POST to /addPlayer.
  4. Flask handles request in app.py add_player().
  5. Flask redirects back to /members.

  Edit Flow:
  1. User clicks "Edit" on a row.
  2. JavaScript reads row data attributes, including unique player id.
  3. JavaScript opens shared player modal in Edit mode.
  4. Form submits POST to /editPlayer with hidden id.
  5. Flask handles request in app.py edit_player().

  Delete Flow:
  1. User clicks "Delete" on a row.
  2. JavaScript reads data-player-id and opens delete modal.
  3. JavaScript writes id into hidden input.
  4. Form submits POST to /deletePlayer.
  5. Flask handles request in app.py delete_player().
*/

document.addEventListener('DOMContentLoaded', function () {
    const ENABLE_MEMBERS_DEBUG_LOGS = false;

    const SEARCH_FILTER_EVENT = 'keyup';
    const MODAL_VISIBLE_DISPLAY = 'flex';
    const MODAL_HIDDEN_DISPLAY = 'none';
    const ROUTE_ADD_PLAYER = '/addPlayer';
    const ROUTE_EDIT_PLAYER = '/editPlayer';
    const ROUTE_DELETE_PLAYER = '/togglePlayerStatus';

    function debugLog(...args) {
        if (!ENABLE_MEMBERS_DEBUG_LOGS) {
            return;
        }
        console.log(...args);
    }

    function debugGroupStart(label) {
        if (!ENABLE_MEMBERS_DEBUG_LOGS) {
            return;
        }
        console.group(label);
    }

    function debugGroupEnd() {
        if (!ENABLE_MEMBERS_DEBUG_LOGS) {
            return;
        }
        console.groupEnd();
    }

    function runDebugFlow(flowLabel, clickMessage, action) {
        debugGroupStart(flowLabel);
        debugLog(clickMessage);
        action();
        debugGroupEnd();
    }

    // Section 1: DOM references used on the Members page.
    const searchInput = document.getElementById('search');
    const searchButton = document.getElementById('search-btn');
    const playerTableRows = document.querySelectorAll('.table-row');
    const addPlayerButton = document.getElementById('add-player-btn');
    const editPlayerButtons = document.querySelectorAll('.edit-player-btn');
    const deletePlayerButtons = document.querySelectorAll('.delete-player-btn');

    const playerModalBackdrop = document.getElementById('player-modal-backdrop');
    const playerModalTitle = document.getElementById('player-modal-title');
    const playerModalCloseButton = document.getElementById('player-modal-close');
    const playerModalCancelButton = document.getElementById('player-modal-cancel');
    const playerModalForm = document.getElementById('player-modal-form');

    const playerIdInput = document.getElementById('player-id');
    const playerFirstNameInput = document.getElementById('first-name');
    const playerLastNameInput = document.getElementById('last-name');
    const playerCityInput = document.getElementById('city');
    const playerRankingInput = document.getElementById('ranking');
    const playerPointsInput = document.getElementById('points');
    const playerDateOfBirthInput = document.getElementById('date-of-birth');
    const playerDateJoinedInput = document.getElementById('date-joined');
    const playerAvatarInput = document.getElementById('avatar');

    const deleteModalBackdrop = document.getElementById('delete-modal-backdrop');
    const deleteModalCloseButton = document.getElementById('delete-modal-close');
    const deleteModalCancelButton = document.getElementById('delete-modal-cancel');
    const deleteModalForm = document.getElementById('delete-modal-form');
    const deletePlayerIdInput = document.getElementById('delete-player-id');

    if (!playerModalBackdrop || !playerModalForm) {
        return;
    }

    // Section 2: Small reusable helpers.
    function setInputValue(inputElement, value) {
        if (!inputElement) {
            return;
        }
        inputElement.value = value;
    }

    function setPlayerFormRouteAndTitle(routePath, titleText) {
        playerModalForm.action = routePath;
        playerModalTitle.textContent = titleText;
    }

    function setPlayerFormValues(values) {
        setInputValue(playerIdInput, values.playerId);
        setInputValue(playerFirstNameInput, values.firstName);
        setInputValue(playerLastNameInput, values.lastName);
        setInputValue(playerCityInput, values.city);
        setInputValue(playerRankingInput, values.ranking);
        setInputValue(playerPointsInput, values.points);
        setInputValue(playerDateOfBirthInput, values.dateOfBirth);
        setInputValue(playerDateJoinedInput, values.dateJoined);

        if (playerAvatarInput) {
            playerAvatarInput.value = '';
        }
    }

    function getPlayerValuesFromRow(playerRow) {
        return {
            playerId: playerRow.dataset.id || '',
            firstName: playerRow.dataset.firstName || '',
            lastName: playerRow.dataset.lastName || '',
            city: playerRow.dataset.city || '',
            ranking: playerRow.dataset.rank || '',
            points: playerRow.dataset.points || 0,
            dateOfBirth: playerRow.dataset.dob ? String(playerRow.dataset.dob).slice(0, 10) : '',
            dateJoined: playerRow.dataset.dateJoined ? String(playerRow.dataset.dateJoined).slice(0, 10) : ''
        };
    }

    function showModal(modalBackdropElement) {
        if (!modalBackdropElement) {
            return;
        }
        modalBackdropElement.style.display = MODAL_VISIBLE_DISPLAY;
        modalBackdropElement.classList.add('is-open');
        modalBackdropElement.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
    }

    function hideModal(modalBackdropElement) {
        if (!modalBackdropElement) {
            return;
        }
        modalBackdropElement.classList.remove('is-open');
        modalBackdropElement.style.display = MODAL_HIDDEN_DISPLAY;
        modalBackdropElement.setAttribute('aria-hidden', 'true');

        // Restore page scrolling when no modal is open.
        if (!isModalVisible(playerModalBackdrop) && !isModalVisible(deleteModalBackdrop)) {
            document.body.style.overflow = '';
        }
    }

    function isModalVisible(modalBackdropElement) {
        return modalBackdropElement && modalBackdropElement.style.display === MODAL_VISIBLE_DISPLAY;
    }

    function filterPlayerRows(searchText, tableRows) {
        const normalizedSearchText = searchText.toLowerCase().trim();

        tableRows.forEach(function (tableRow) {
            const normalizedRowText = tableRow.textContent.toLowerCase();
            tableRow.style.display = normalizedRowText.includes(normalizedSearchText) ? '' : 'none';
        });
    }

    function closePlayerModal() {
        hideModal(playerModalBackdrop);
    }

    function closeDeletePlayerModal() {
        hideModal(deleteModalBackdrop);
    }

    function bindModalCloseHandlers(
        modalBackdropElement,
        closeButtonElement,
        cancelButtonElement,
        closeHandler,
        options
    ) {
        const config = options || {};
        const enableCloseButton = config.enableCloseButton !== false;
        const enableBackdropClose = config.enableBackdropClose !== false;

        if (closeButtonElement && enableCloseButton) {
            closeButtonElement.addEventListener('click', closeHandler);
        }

        if (cancelButtonElement) {
            cancelButtonElement.addEventListener('click', closeHandler);
        }

        if (modalBackdropElement && enableBackdropClose) {
            modalBackdropElement.addEventListener('click', function (event) {
                if (event.target === modalBackdropElement) {
                    closeHandler();
                }
            });
        }
    }

    function openPlayerModalForAdd() {
        // Add and Edit use the same modal form.
        // Add mode posts to /addPlayer.
        debugLog('[Members][Add] Opening Add Modal');

        setPlayerFormRouteAndTitle(ROUTE_ADD_PLAYER, 'Add Player');
        setPlayerFormValues({
            playerId: '',
            firstName: '',
            lastName: '',
            city: '',
            ranking: '',
            points: 0,
            dateOfBirth: '',
            dateJoined: ''
        });

        showModal(playerModalBackdrop);
        playerFirstNameInput.focus();
    }

    function openPlayerModalForEdit(playerRow) {
        // Edit mode reuses the same form and posts to /editPlayer.
        // The player id comes from row data attributes -> hidden input name="id" -> Flask route.
        const playerValues = getPlayerValuesFromRow(playerRow);
        const playerId = playerValues.playerId || 'unknown';

        debugLog('[Members][Edit] Opening Edit Modal for playerId: ' + playerId);
        setPlayerFormRouteAndTitle(ROUTE_EDIT_PLAYER, 'Edit Player');
        setPlayerFormValues(playerValues);

        showModal(playerModalBackdrop);
        playerFirstNameInput.focus();
    }

        function openDeletePlayerModal(playerId, isActive) {
                // Toggle flow:
                // Delete button data-player-id -> JS sets hidden input #delete-player-id ->
                // form POST /togglePlayerStatus -> toggle_player_status() in app.py.
                // playerId is the unique identifier. We do not use names because names can repeat.
                debugLog('[Members][Delete] Opening Delete Modal for playerId: ' + playerId);
                debugLog('[Members][Delete] Setting hidden delete id field to: ' + playerId);

                setInputValue(deletePlayerIdInput, playerId);
                const confirmBtn = deleteModalForm
                    ? deleteModalForm.querySelector('[type="submit"]')
                    : null;
                const modalTitle = document.getElementById('delete-modal-title');
                if (confirmBtn) {
                    confirmBtn.textContent = isActive === '1' ? 'Deactivate' : 'Activate';
                }
                if (modalTitle) {
                    modalTitle.textContent = isActive === '1' ? 'Deactivate Player' : 'Activate Player';
                }
                showModal(deleteModalBackdrop);
    }

    function openEditModalFromUrlIfRequested() {
        const urlParams = new URLSearchParams(window.location.search);
        const editId = urlParams.get('editId');
        if (!editId) {
            return;
        }

        const playerRow = document.querySelector('.table-row[data-id="' + editId + '"]');
        if (!playerRow) {
            return;
        }

        openPlayerModalForEdit(playerRow);

        // Keep the user on the same clean members URL after opening the dialog.
        urlParams.delete('editId');
        const queryString = urlParams.toString();
        const nextUrl = queryString ? window.location.pathname + '?' + queryString : window.location.pathname;
        window.history.replaceState({}, '', nextUrl);
    }

    // Section 3: Event listeners (click -> JS -> form submit -> Flask route).
    function runSearch() {
        filterPlayerRows(searchInput.value, playerTableRows);
    }

    if (searchInput) {
        searchInput.addEventListener(SEARCH_FILTER_EVENT, runSearch);
        searchInput.addEventListener('keydown', function (event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                runSearch();
            }
        });
    }

    if (searchButton) {
        searchButton.addEventListener('click', runSearch);
    }

    if (addPlayerButton) {
        addPlayerButton.addEventListener('click', function () {
            runDebugFlow('[Members][Add] Flow', '[Members][Add] Add button clicked', function () {
                openPlayerModalForAdd();
            });
        });
    }

    editPlayerButtons.forEach(function (editButton) {
        editButton.addEventListener('click', function () {
            const playerRow = editButton.closest('.table-row');
            if (!playerRow) {
                return;
            }

            // playerRow.dataset.id is the single source of truth for the player identity.
            // We use this id (not player name) because names are not guaranteed unique.
            runDebugFlow(
                '[Members][Edit] Flow',
                '[Members][Edit] Edit button clicked for playerId: ' + (playerRow.dataset.id || 'unknown'),
                function () {
                    openPlayerModalForEdit(playerRow);
                }
            );
        });
    });

    deletePlayerButtons.forEach(function (deleteButton) {
        deleteButton.addEventListener('click', function () {
            // data-player-id comes from the HTML button rendered per table row.
            const playerId = deleteButton.dataset.playerId || '';
            if (!playerId) {
                return;
            }

            const isActive = deleteButton.dataset.isActive || '1';

            runDebugFlow(
                '[Members][Delete] Flow',
                '[Members][Delete] Delete button clicked for playerId: ' + playerId,
                function () {
                    openDeletePlayerModal(playerId, isActive);
                }
            );
        });
    });

    bindModalCloseHandlers(playerModalBackdrop, playerModalCloseButton, playerModalCancelButton, closePlayerModal, {
        enableCloseButton: false,
        enableBackdropClose: false
    });
    bindModalCloseHandlers(deleteModalBackdrop, deleteModalCloseButton, deleteModalCancelButton, closeDeletePlayerModal);

    if (deleteModalForm) {
        // This form posts to /deletePlayer in app.py.
        deleteModalForm.addEventListener('submit', function () {
            debugLog('[Members][Delete] Submitting Delete Form to ' + ROUTE_DELETE_PLAYER);
            closeDeletePlayerModal();
        });
    }

    if (playerModalForm) {
        // Shared player modal submits to /addPlayer or /editPlayer based on modal mode.
        playerModalForm.addEventListener('submit', function () {
            const routePath = playerModalForm.getAttribute('action') || ROUTE_ADD_PLAYER;

            if (routePath === ROUTE_ADD_PLAYER) {
                debugLog('[Members][Add] Submitting Add Form to ' + ROUTE_ADD_PLAYER);
            } else if (routePath === ROUTE_EDIT_PLAYER) {
                debugLog('[Members][Edit] Submitting Edit Form to ' + ROUTE_EDIT_PLAYER);
            }
        });
    }

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && isModalVisible(deleteModalBackdrop)) {
            closeDeletePlayerModal();
        }
    });

    // Deep link support: /members?editId=<player_id> opens Edit modal directly.
    openEditModalFromUrlIfRequested();
});
