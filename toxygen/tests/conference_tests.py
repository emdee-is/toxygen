if False:
    @unittest.skip # to yet
    def test_conference(self):
        """
        t:group_new
        t:conference_delete
        t:conference_get_chatlist_size
        t:conference_get_chatlist
        t:conference_send_message
        """
        bob_addr = self.bob.self_get_address()
        alice_addr = self.alice.self_get_address()

        self.abid = self.alice.friend_by_public_key(bob_addr)
        self.baid = self.bob.friend_by_public_key(alice_addr)

        assert self.bob_just_add_alice_as_friend()

        #: Test group add
        privacy_state = enums.TOX_GROUP_PRIVACY_STATE['PUBLIC']
        group_name = 'test_group'
        nick = 'test_nick'
        status = None # dunno
        self.group_id = self.bob.group_new(privacy_state, group_name, nick, status)
        # :return group number on success, UINT32_MAX on failure.
        assert self.group_id >= 0

        self.loop(50)

        BID = self.abid

        def alices_on_conference_invite(self, fid, type_, data):
            assert fid == BID
            assert type_ == 0
            gn = self.conference_join(fid, data)
            assert type_ == self.conference_get_type(gn)
            self.gi = True

        def alices_on_conference_peer_list_changed(self, gid):
            logging.debug("alices_on_conference_peer_list_changed")
            assert gid == self.group_id
            self.gn = True

        try:
            AliceTox.on_conference_invite = alices_on_conference_invite
            AliceTox.on_conference_peer_list_changed = alices_on_conference_peer_list_changed

            self.alice.gi = False
            self.alice.gn = False

            self.wait_ensure_exec(self.bob.conference_invite, (self.aid, self.group_id))

            assert self.wait_callback_trues(self.alice, ['gi', 'gn'])
        except AssertionError as e:
            raise
        finally:
            AliceTox.on_conference_invite = Tox.on_conference_invite
            AliceTox.on_conference_peer_list_change = Tox.on_conference_peer_list_changed

        #: Test group number of peers
        self.loop(50)
        assert self.bob.conference_peer_count(self.group_id) == 2

        #: Test group peername
        self.alice.self_set_name('Alice')
        self.bob.self_set_name('Bob')

        def alices_on_conference_peer_list_changed(self, gid):
            logging.debug("alices_on_conference_peer_list_changed")
            self.gn = True
        try:
            AliceTox.on_conference_peer_list_changed = alices_on_conference_peer_list_changed
            self.alice.gn = False

            assert self.wait_callback_true(self.alice, 'gn')
        except AssertionError as e:
            raise
        finally:
            AliceTox.on_conference_peer_list_changed = Tox.on_conference_peer_list_changed

        peernames = [self.bob.conference_peer_get_name(self.group_id, i) for i in
                     range(self.bob.conference_peer_count(self.group_id))]
        assert 'Alice' in peernames
        assert 'Bob' in peernames

        #: Test title change
        self.bob.conference_set_title(self.group_id, 'My special title')
        assert self.bob.conference_get_title(self.group_id) == 'My special title'

        #: Test group message
        AID = self.aid
        BID = self.bid
        MSG = 'Group message test'

        def alices_on_conference_message(self, gid, fgid, msg_type, message):
            logging.debug("alices_on_conference_message" +repr(message))
            if fgid == AID:
                assert gid == self.group_id
                assert str(message, 'UTF-8') == MSG
                self.alice.gm = True

        try:
            AliceTox.on_conference_message = alices_on_conference_message
            self.alice.gm = False

            self.wait_ensure_exec(self.bob.conference_send_message, (
                self.group_id, TOX_MESSAGE_TYPE['NORMAL'], MSG))
            assert self.wait_callback_true(self.alice, 'gm')
        except AssertionError as e:
            raise
        finally:
            AliceTox.on_conference_message = Tox.on_conference_message

        #: Test group action
        AID = self.aid
        BID = self.bid
        MSG = 'Group action test'

        def on_conference_action(self, gid, fgid, msg_type, action):
            if fgid == AID:
                assert gid == self.group_id
                assert msg_type == TOX_MESSAGE_TYPE['ACTION']
                assert str(action, 'UTF-8') == MSG
                self.ga = True

        try:
            AliceTox.on_conference_message = on_conference_action
            self.alice.ga = False

            self.wait_ensure_exec(self.bob.conference_send_message,
                             (self.group_id, TOX_MESSAGE_TYPE['ACTION'], MSG))

            assert self.wait_callback_true(self.alice, 'ga')

            #: Test chatlist
            assert len(self.bob.conference_get_chatlist()) == self.bob.conference_get_chatlist_size(), \
              print(len(self.bob.conference_get_chatlist()), '!=', self.bob.conference_get_chatlist_size())
            assert len(self.alice.conference_get_chatlist()) == self.bob.conference_get_chatlist_size(), \
              print(len(self.alice.conference_get_chatlist()), '!=', self.bob.conference_get_chatlist_size())
            assert self.bob.conference_get_chatlist_size() == 1, \
              self.bob.conference_get_chatlist_size()
            self.bob.conference_delete(self.group_id)
            assert self.bob.conference_get_chatlist_size() == 0, \
              self.bob.conference_get_chatlist_size()

        except AssertionError as e:
            raise
        finally:
            AliceTox.on_conference_message = Tox.on_conference_message


