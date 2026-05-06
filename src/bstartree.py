import math


class BStarTreeNode:
    """
    A node in a B* tree.

    This implementation follows the B-tree-based interpretation
    required by the project manual.

    Internal nodes may store key-RID pairs.
    Search may terminate at internal nodes.
    """

    def __init__(self, is_leaf=True):
        self.is_leaf = is_leaf
        self.keys = []
        self.rids = []
        self.children = []


class BStarTree:
    """
    B* tree index structure.

    In this implementation:
    - d is interpreted as maximum fan-out order.
    - max_keys = d - 1
    - min_keys = ceil(d / 2) - 1

    B*-specific insertion policies such as sibling redistribution
    and 2-to-3 split will be added in later phases.
    """

    def __init__(self, d):
        if d < 3:
            raise ValueError("B* tree order d must be at least 3")

        self.d = d
        self.max_keys = d - 1
        self.min_keys = math.ceil(d / 2) - 1

        self.root = BStarTreeNode(is_leaf=True)

        self.num_splits = 0
        self.num_redistributions = 0
        self.num_2_to_3_splits = 0

    def search(self, key):
        """
        Search for key in the B* tree.

        Since this B* tree extends the B-tree implementation,
        internal nodes may contain actual key-RID pairs.
        Therefore, search may terminate at an internal node.
        """

        return self._search_node(self.root, key)

    def _search_node(self, node, key):
        i = 0

        while i < len(node.keys) and key > node.keys[i]:
            i += 1

        if i < len(node.keys) and key == node.keys[i]:
            return node.rids[i]

        if node.is_leaf:
            return None

        return self._search_node(node.children[i], key)

    def insert(self, key, rid):
        """
        Insert a key-RID pair into the B* tree.

        Current phase:
        - supports root leaf insert
        - supports root leaf split
        - supports insertion into a non-root leaf
        - handles non-root leaf overflow by redistribution with left sibling
        """

        existing_rid = self.search(key)
        if existing_rid is not None:
            raise ValueError(f"Duplicate key insertion is not allowed: {key}")

        leaf, path = self._find_leaf_with_path(key)
        self._insert_into_leaf(leaf, key, rid)

        if len(leaf.keys) <= self.max_keys:
            return

        # Root leaf overflow.
        if leaf is self.root:
            self._split_root_leaf()
            return

        # Non-root leaf overflow.
        self._handle_leaf_overflow(leaf, path)

    def _find_leaf_with_path(self, key):
        """
        Find the leaf node where the key should be inserted.

        Returns:
            leaf: target leaf node
            path: list of (parent_node, child_index) pairs

        This path will be used later for redistribution and 2-to-3 split.
        """

        current = self.root
        path = []

        while not current.is_leaf:
            i = 0

            while i < len(current.keys) and key > current.keys[i]:
                i += 1

            path.append((current, i))
            current = current.children[i]

        return current, path

    def _handle_leaf_overflow(self, leaf, path):
        """
        Handle overflow in a non-root leaf node.

        Current supported B* policy:
        - try redistribution with the left sibling if it has space
        - do not split if redistribution is possible

        2-to-3 split will be implemented in the next phase.
        """

        parent, child_index = path[-1]

        if (
            child_index > 0
            and parent.children[child_index - 1].is_leaf
            and len(parent.children[child_index - 1].keys) < self.max_keys
        ):
            self._redistribute_leaf_with_left(parent, child_index)
            return

        if (
            child_index + 1 < len(parent.children)
            and parent.children[child_index + 1].is_leaf
            and len(parent.children[child_index + 1].keys) < self.max_keys
        ):
            self._redistribute_leaf_with_right(parent, child_index)
            return

        if child_index > 0 and parent.children[child_index - 1].is_leaf:
            self._split_two_leaf_nodes_into_three(parent, child_index - 1, path[:-1])
            return

        if child_index + 1 < len(parent.children) and parent.children[child_index + 1].is_leaf:
            self._split_two_leaf_nodes_into_three(parent, child_index, path[:-1])
            return

        raise RuntimeError("No valid sibling found for B* 2-to-3 leaf split")

    def _handle_internal_overflow(self, node, path):
        """
        Handle overflow in an internal node.

        B* policy:
        - try redistribution with internal siblings first
        - if redistribution is impossible, perform 2-to-3 internal split
        - if the root overflows, split the root
        """

        if node is self.root or not path:
            self._split_root_internal()
            return

        parent, child_index = path[-1]

        if (
            child_index > 0
            and not parent.children[child_index - 1].is_leaf
            and len(parent.children[child_index - 1].keys) < self.max_keys
        ):
            self._redistribute_internal_with_left(parent, child_index)
            return

        if (
            child_index + 1 < len(parent.children)
            and not parent.children[child_index + 1].is_leaf
            and len(parent.children[child_index + 1].keys) < self.max_keys
        ):
            self._redistribute_internal_with_right(parent, child_index)
            return

        if child_index > 0 and not parent.children[child_index - 1].is_leaf:
            self._split_two_internal_nodes_into_three(parent, child_index - 1, path[:-1])
            return

        if (
            child_index + 1 < len(parent.children)
            and not parent.children[child_index + 1].is_leaf
        ):
            self._split_two_internal_nodes_into_three(parent, child_index, path[:-1])
            return

        raise RuntimeError("No valid sibling found for B* internal overflow")

    def _split_root_leaf(self):
        """
        Split an overflow root leaf.

        Since the root has no sibling, B*-tree redistribution cannot be applied here.
        This creates a new internal root.

        B*-tree is implemented as a B-tree extension, so the promoted key is moved
        to the parent and removed from the leaf nodes.
        """

        old_root = self.root

        median_index = len(old_root.keys) // 2

        promoted_key = old_root.keys[median_index]
        promoted_rid = old_root.rids[median_index]

        left = BStarTreeNode(is_leaf=True)
        right = BStarTreeNode(is_leaf=True)

        left.keys = old_root.keys[:median_index]
        left.rids = old_root.rids[:median_index]

        right.keys = old_root.keys[median_index + 1:]
        right.rids = old_root.rids[median_index + 1:]

        new_root = BStarTreeNode(is_leaf=False)
        new_root.keys = [promoted_key]
        new_root.rids = [promoted_rid]
        new_root.children = [left, right]

        self.root = new_root
        self.num_splits += 1

    def _insert_into_leaf(self, leaf, key, rid):
        """
        Insert key-RID pair into a leaf node while keeping keys sorted.
        """

        i = len(leaf.keys) - 1

        leaf.keys.append(None)
        leaf.rids.append(None)

        while i >= 0 and key < leaf.keys[i]:
            leaf.keys[i + 1] = leaf.keys[i]
            leaf.rids[i + 1] = leaf.rids[i]
            i -= 1

        leaf.keys[i + 1] = key
        leaf.rids[i + 1] = rid

    def _redistribute_leaf_with_left(self, parent, child_index):
        """
        Redistribute keys among:
        - left sibling
        - parent separator key
        - overflowing leaf child

        This is a B*-tree overflow policy.
        If the left sibling has available space, we avoid splitting.
        """

        left_sibling = parent.children[child_index - 1]
        child = parent.children[child_index]

        separator_key = parent.keys[child_index - 1]
        separator_rid = parent.rids[child_index - 1]

        combined = []

        for key, rid in zip(left_sibling.keys, left_sibling.rids):
            combined.append((key, rid))

        combined.append((separator_key, separator_rid))

        for key, rid in zip(child.keys, child.rids):
            combined.append((key, rid))

        combined.sort(key=lambda pair: pair[0])

        left_count = len(combined) // 2

        left_pairs = combined[:left_count]
        separator_pair = combined[left_count]
        right_pairs = combined[left_count + 1:]

        left_sibling.keys = [key for key, _ in left_pairs]
        left_sibling.rids = [rid for _, rid in left_pairs]

        parent.keys[child_index - 1] = separator_pair[0]
        parent.rids[child_index - 1] = separator_pair[1]

        child.keys = [key for key, _ in right_pairs]
        child.rids = [rid for _, rid in right_pairs]

        self.num_redistributions += 1

    def _redistribute_internal_with_left(self, parent, child_index):
        """
        Redistribute keys/children among:
        - left internal sibling
        - parent separator
        - overflowing internal child
        """

        left_sibling = parent.children[child_index - 1]
        child = parent.children[child_index]

        separator_pair = (
            parent.keys[child_index - 1],
            parent.rids[child_index - 1],
        )

        combined_pairs = []
        combined_pairs.extend(zip(left_sibling.keys, left_sibling.rids))
        combined_pairs.append(separator_pair)
        combined_pairs.extend(zip(child.keys, child.rids))

        combined_children = left_sibling.children + child.children

        split_index = len(combined_pairs) // 2

        left_pairs = combined_pairs[:split_index]
        new_separator = combined_pairs[split_index]
        right_pairs = combined_pairs[split_index + 1:]

        left_sibling.keys = [key for key, _ in left_pairs]
        left_sibling.rids = [rid for _, rid in left_pairs]
        left_sibling.children = combined_children[:split_index + 1]

        parent.keys[child_index - 1] = new_separator[0]
        parent.rids[child_index - 1] = new_separator[1]

        child.keys = [key for key, _ in right_pairs]
        child.rids = [rid for _, rid in right_pairs]
        child.children = combined_children[split_index + 1:]

        self.num_redistributions += 1

    def _redistribute_leaf_with_right(self, parent, child_index):
        """
        Redistribute keys among:
        - overflowing leaf child
        - parent separator key
        - right sibling

        This avoids splitting when the right sibling has available space.
        """

        child = parent.children[child_index]
        right_sibling = parent.children[child_index + 1]

        separator_key = parent.keys[child_index]
        separator_rid = parent.rids[child_index]

        combined = []

        for key, rid in zip(child.keys, child.rids):
            combined.append((key, rid))

        combined.append((separator_key, separator_rid))

        for key, rid in zip(right_sibling.keys, right_sibling.rids):
            combined.append((key, rid))

        combined.sort(key=lambda pair: pair[0])

        left_count = len(combined) // 2

        left_pairs = combined[:left_count]
        separator_pair = combined[left_count]
        right_pairs = combined[left_count + 1:]

        child.keys = [key for key, _ in left_pairs]
        child.rids = [rid for _, rid in left_pairs]

        parent.keys[child_index] = separator_pair[0]
        parent.rids[child_index] = separator_pair[1]

        right_sibling.keys = [key for key, _ in right_pairs]
        right_sibling.rids = [rid for _, rid in right_pairs]

        self.num_redistributions += 1

    def _redistribute_internal_with_right(self, parent, child_index):
        """
        Redistribute keys/children among:
        - overflowing internal child
        - parent separator
        - right internal sibling
        """

        child = parent.children[child_index]
        right_sibling = parent.children[child_index + 1]

        separator_pair = (
            parent.keys[child_index],
            parent.rids[child_index],
        )

        combined_pairs = []
        combined_pairs.extend(zip(child.keys, child.rids))
        combined_pairs.append(separator_pair)
        combined_pairs.extend(zip(right_sibling.keys, right_sibling.rids))

        combined_children = child.children + right_sibling.children

        split_index = len(combined_pairs) // 2

        left_pairs = combined_pairs[:split_index]
        new_separator = combined_pairs[split_index]
        right_pairs = combined_pairs[split_index + 1:]

        child.keys = [key for key, _ in left_pairs]
        child.rids = [rid for _, rid in left_pairs]
        child.children = combined_children[:split_index + 1]

        parent.keys[child_index] = new_separator[0]
        parent.rids[child_index] = new_separator[1]

        right_sibling.keys = [key for key, _ in right_pairs]
        right_sibling.rids = [rid for _, rid in right_pairs]
        right_sibling.children = combined_children[split_index + 1:]

        self.num_redistributions += 1

    def _split_two_leaf_nodes_into_three(self, parent, left_index, parent_path):
        """
        Perform B* 2-to-3 split on two adjacent leaf children.

        This combines:
        - left leaf
        - parent separator key
        - right leaf

        Then redistributes them into:
        - left leaf
        - first parent separator
        - middle leaf
        - second parent separator
        - right leaf

        Note:
        This B* tree is B-tree-based, so parent separator keys are actual
        key-RID pairs and are included in redistribution.
        """

        left_leaf = parent.children[left_index]
        right_leaf = parent.children[left_index + 1]

        separator_key = parent.keys[left_index]
        separator_rid = parent.rids[left_index]

        combined = []

        for key, rid in zip(left_leaf.keys, left_leaf.rids):
            combined.append((key, rid))

        combined.append((separator_key, separator_rid))

        for key, rid in zip(right_leaf.keys, right_leaf.rids):
            combined.append((key, rid))

        combined.sort(key=lambda pair: pair[0])

        total = len(combined)

        first_sep_index = total // 3
        second_sep_index = (2 * total) // 3

        left_pairs = combined[:first_sep_index]
        first_separator = combined[first_sep_index]

        middle_pairs = combined[first_sep_index + 1:second_sep_index]
        second_separator = combined[second_sep_index]

        right_pairs = combined[second_sep_index + 1:]

        middle_leaf = BStarTreeNode(is_leaf=True)

        left_leaf.keys = [key for key, _ in left_pairs]
        left_leaf.rids = [rid for _, rid in left_pairs]

        middle_leaf.keys = [key for key, _ in middle_pairs]
        middle_leaf.rids = [rid for _, rid in middle_pairs]

        right_leaf.keys = [key for key, _ in right_pairs]
        right_leaf.rids = [rid for _, rid in right_pairs]

        parent.keys[left_index] = first_separator[0]
        parent.rids[left_index] = first_separator[1]

        parent.keys.insert(left_index + 1, second_separator[0])
        parent.rids.insert(left_index + 1, second_separator[1])

        parent.children.insert(left_index + 1, middle_leaf)

        self.num_2_to_3_splits += 1
        self.num_splits += 1

        if len(parent.keys) > self.max_keys:
            self._handle_internal_overflow(parent, parent_path)

    def _split_two_internal_nodes_into_three(self, parent, left_index, parent_path):
        """
        Perform B* 2-to-3 split on two adjacent internal children.

        This combines:
        - left internal child
        - parent separator
        - right internal child

        Then redistributes into:
        - left internal child
        - first parent separator
        - middle internal child
        - second parent separator
        - right internal child
        """

        left_child = parent.children[left_index]
        right_child = parent.children[left_index + 1]

        separator_pair = (
            parent.keys[left_index],
            parent.rids[left_index],
        )

        combined_pairs = []
        combined_pairs.extend(zip(left_child.keys, left_child.rids))
        combined_pairs.append(separator_pair)
        combined_pairs.extend(zip(right_child.keys, right_child.rids))

        combined_children = left_child.children + right_child.children

        total = len(combined_pairs)

        first_sep_index = total // 3
        second_sep_index = (2 * total) // 3

        left_pairs = combined_pairs[:first_sep_index]
        first_separator = combined_pairs[first_sep_index]

        middle_pairs = combined_pairs[first_sep_index + 1:second_sep_index]
        second_separator = combined_pairs[second_sep_index]

        right_pairs = combined_pairs[second_sep_index + 1:]

        middle_child = BStarTreeNode(is_leaf=False)

        left_child.keys = [key for key, _ in left_pairs]
        left_child.rids = [rid for _, rid in left_pairs]
        left_child.children = combined_children[:first_sep_index + 1]

        middle_child.keys = [key for key, _ in middle_pairs]
        middle_child.rids = [rid for _, rid in middle_pairs]
        middle_child.children = combined_children[first_sep_index + 1:second_sep_index + 1]

        right_child.keys = [key for key, _ in right_pairs]
        right_child.rids = [rid for _, rid in right_pairs]
        right_child.children = combined_children[second_sep_index + 1:]

        parent.keys[left_index] = first_separator[0]
        parent.rids[left_index] = first_separator[1]

        parent.keys.insert(left_index + 1, second_separator[0])
        parent.rids.insert(left_index + 1, second_separator[1])

        parent.children.insert(left_index + 1, middle_child)

        self.num_2_to_3_splits += 1
        self.num_splits += 1

        if len(parent.keys) > self.max_keys:
            self._handle_internal_overflow(parent, parent_path)

    def _split_root_internal(self):
        """
        Split an overflow internal root node.

        Since the root has no sibling, B*-style redistribution with siblings
        cannot be applied. Therefore, the overflowing root is split and a new
        root is created.

        This is B-tree-style internal split:
        - median key-RID pair moves up to the new root
        - left keys/children remain in the left internal node
        - right keys/children move to the right internal node
        """

        old_root = self.root

        median_index = len(old_root.keys) // 2

        promoted_key = old_root.keys[median_index]
        promoted_rid = old_root.rids[median_index]

        left = BStarTreeNode(is_leaf=False)
        right = BStarTreeNode(is_leaf=False)

        left.keys = old_root.keys[:median_index]
        left.rids = old_root.rids[:median_index]
        left.children = old_root.children[:median_index + 1]

        right.keys = old_root.keys[median_index + 1:]
        right.rids = old_root.rids[median_index + 1:]
        right.children = old_root.children[median_index + 1:]

        new_root = BStarTreeNode(is_leaf=False)
        new_root.keys = [promoted_key]
        new_root.rids = [promoted_rid]
        new_root.children = [left, right]

        self.root = new_root
        self.num_splits += 1

    def delete(self, key):
        """
        Delete a key from the B* tree.

        Supports:
        - deleting from a leaf node
        - deleting from an internal node using predecessor replacement
        - leaf underflow handling by borrow or merge
        - internal underflow handling after child merge
        - root shrink
        """

        node, key_index, path = self._find_key_with_path(key)

        if node is None:
            return False

        if node.is_leaf:
            node.keys.pop(key_index)
            node.rids.pop(key_index)

            if node is self.root:
                return True

            if len(node.keys) < self.min_keys:
                parent, child_index = path[-1]
                self._handle_leaf_underflow(parent, child_index)

            self._repair_internal_underflow_from_path(path)

            while not self.root.is_leaf and len(self.root.keys) == 0:
                self.root = self.root.children[0]

            return True

        predecessor_node, predecessor_index, predecessor_path = (
            self._find_predecessor_node_with_path(node, key_index, path)
        )

        predecessor_key = predecessor_node.keys[predecessor_index]
        predecessor_rid = predecessor_node.rids[predecessor_index]

        node.keys[key_index] = predecessor_key
        node.rids[key_index] = predecessor_rid

        predecessor_node.keys.pop(predecessor_index)
        predecessor_node.rids.pop(predecessor_index)

        if predecessor_node is not self.root and len(predecessor_node.keys) < self.min_keys:
            parent, child_index = predecessor_path[-1]
            self._handle_leaf_underflow(parent, child_index)

        self._repair_internal_underflow_from_path(predecessor_path)

        while not self.root.is_leaf and len(self.root.keys) == 0:
            self.root = self.root.children[0]

        return True

    def _repair_internal_underflow_from_path(self, path):
        """
        Repair internal node underflow from bottom to top.

        path contains (parent, child_index) pairs used to reach the original node.
        """

        for level in range(len(path) - 2, -1, -1):
            parent, child_index = path[level]

            if child_index >= len(parent.children):
                child_index = len(parent.children) - 1

            child = parent.children[child_index]

            if (
                not child.is_leaf
                and child is not self.root
                and len(child.keys) < self.min_keys
            ):
                self._handle_internal_underflow(parent, child_index)

    def _find_predecessor_node_with_path(self, node, key_index, path_to_node):
        """
        Find the predecessor of node.keys[key_index].

        Predecessor is the largest key in the left subtree.

        Returns:
            predecessor_node
            predecessor_index
            predecessor_path
        """

        current = node.children[key_index]
        path = path_to_node[:]
        path.append((node, key_index))

        while not current.is_leaf:
            child_index = len(current.children) - 1
            path.append((current, child_index))
            current = current.children[child_index]

        predecessor_index = len(current.keys) - 1

        return current, predecessor_index, path

    def _find_key_with_path(self, key):
        """
        Find the node containing the key.

        Returns:
            node: node containing key, or None
            key_index: index of key in node, or None
            path: list of (parent_node, child_index) pairs
        """

        current = self.root
        path = []

        while True:
            i = 0

            while i < len(current.keys) and key > current.keys[i]:
                i += 1

            if i < len(current.keys) and key == current.keys[i]:
                return current, i, path

            if current.is_leaf:
                return None, None, path

            path.append((current, i))
            current = current.children[i]

    def _handle_leaf_underflow(self, parent, child_index):
        """
        Handle underflow in a leaf child.

        Policy:
        - borrow from left sibling if possible
        - otherwise borrow from right sibling if possible
        - otherwise merge with a sibling
        """

        if (
            child_index > 0
            and parent.children[child_index - 1].is_leaf
            and len(parent.children[child_index - 1].keys) > self.min_keys
        ):
            self._borrow_leaf_from_prev(parent, child_index)
            return

        if (
            child_index + 1 < len(parent.children)
            and parent.children[child_index + 1].is_leaf
            and len(parent.children[child_index + 1].keys) > self.min_keys
        ):
            self._borrow_leaf_from_next(parent, child_index)
            return

        if child_index + 1 < len(parent.children):
            self._merge_leaf_with_next(parent, child_index)
            return

        self._merge_leaf_with_next(parent, child_index - 1)

    def _handle_internal_underflow(self, parent, child_index):
        """
        Handle underflow in an internal child.

        Deletion policy:
        - borrow from left internal sibling if possible
        - otherwise borrow from right internal sibling if possible
        - otherwise merge with a sibling
        """

        if (
            child_index > 0
            and not parent.children[child_index - 1].is_leaf
            and len(parent.children[child_index - 1].keys) > self.min_keys
        ):
            self._borrow_internal_from_prev(parent, child_index)
            return

        if (
            child_index + 1 < len(parent.children)
            and not parent.children[child_index + 1].is_leaf
            and len(parent.children[child_index + 1].keys) > self.min_keys
        ):
            self._borrow_internal_from_next(parent, child_index)
            return

        if child_index + 1 < len(parent.children):
            self._merge_internal_with_next(parent, child_index)
            return

        self._merge_internal_with_next(parent, child_index - 1)

    def _borrow_leaf_from_prev(self, parent, child_index):
        """
        Borrow one key-RID pair from the left leaf sibling.

        B-tree-style borrow:
        - parent separator moves down to child
        - left sibling's largest key moves up to parent
        """

        child = parent.children[child_index]
        left_sibling = parent.children[child_index - 1]

        child.keys.insert(0, parent.keys[child_index - 1])
        child.rids.insert(0, parent.rids[child_index - 1])

        parent.keys[child_index - 1] = left_sibling.keys.pop()
        parent.rids[child_index - 1] = left_sibling.rids.pop()

    def _borrow_internal_from_prev(self, parent, child_index):
        """
        Borrow from the left internal sibling.

        B-tree-style internal borrow:
        - parent separator moves down to child
        - left sibling's largest key moves up to parent
        - one child pointer moves from left sibling to child
        """

        child = parent.children[child_index]
        left_sibling = parent.children[child_index - 1]

        child.keys.insert(0, parent.keys[child_index - 1])
        child.rids.insert(0, parent.rids[child_index - 1])
        child.children.insert(0, left_sibling.children.pop())

        parent.keys[child_index - 1] = left_sibling.keys.pop()
        parent.rids[child_index - 1] = left_sibling.rids.pop()

    def _borrow_leaf_from_next(self, parent, child_index):
        """
        Borrow one key-RID pair from the right leaf sibling.

        B-tree-style borrow:
        - parent separator moves down to child
        - right sibling's smallest key moves up to parent
        """

        child = parent.children[child_index]
        right_sibling = parent.children[child_index + 1]

        child.keys.append(parent.keys[child_index])
        child.rids.append(parent.rids[child_index])

        parent.keys[child_index] = right_sibling.keys.pop(0)
        parent.rids[child_index] = right_sibling.rids.pop(0)

    def _borrow_internal_from_next(self, parent, child_index):
        """
        Borrow from the right internal sibling.

        B-tree-style internal borrow:
        - parent separator moves down to child
        - right sibling's smallest key moves up to parent
        - one child pointer moves from right sibling to child
        """

        child = parent.children[child_index]
        right_sibling = parent.children[child_index + 1]

        child.keys.append(parent.keys[child_index])
        child.rids.append(parent.rids[child_index])
        child.children.append(right_sibling.children.pop(0))

        parent.keys[child_index] = right_sibling.keys.pop(0)
        parent.rids[child_index] = right_sibling.rids.pop(0)

    def _merge_leaf_with_next(self, parent, left_index):
        """
        Merge two adjacent leaf children with the parent separator.

        B*-tree here is B-tree-based, so the parent separator is an actual
        key-RID pair. Therefore, during leaf merge:

            left leaf + parent separator + right leaf

        are combined into one leaf.
        """

        left_child = parent.children[left_index]
        right_child = parent.children[left_index + 1]

        separator_key = parent.keys.pop(left_index)
        separator_rid = parent.rids.pop(left_index)

        left_child.keys.append(separator_key)
        left_child.rids.append(separator_rid)

        left_child.keys.extend(right_child.keys)
        left_child.rids.extend(right_child.rids)

        parent.children.pop(left_index + 1)

    def _merge_internal_with_next(self, parent, left_index):
        """
        Merge two adjacent internal children with the parent separator.

        B-tree-style internal merge:
            left internal + parent separator + right internal
        """

        left_child = parent.children[left_index]
        right_child = parent.children[left_index + 1]

        separator_key = parent.keys.pop(left_index)
        separator_rid = parent.rids.pop(left_index)

        left_child.keys.append(separator_key)
        left_child.rids.append(separator_rid)

        left_child.keys.extend(right_child.keys)
        left_child.rids.extend(right_child.rids)

        left_child.children.extend(right_child.children)

        parent.children.pop(left_index + 1)

    def range_query(self, low_key, high_key):
        """
        Return all (key, rid) pairs such that low_key <= key <= high_key.

        Since this B* tree is B-tree-based, internal nodes may also contain
        actual key-RID pairs. Therefore, range query is implemented using
        inorder traversal instead of leaf linked-list scan.
        """

        if low_key > high_key:
            return []

        result = []
        self._range_query_node(self.root, low_key, high_key, result)
        return result

    def _range_query_node(self, node, low_key, high_key, result):
        """
        Inorder range traversal for B-tree-style B* tree.
        """

        if node.is_leaf:
            for key, rid in zip(node.keys, node.rids):
                if low_key <= key <= high_key:
                    result.append((key, rid))
            return

        for i in range(len(node.keys)):
            # Traverse left child of key i.
            self._range_query_node(node.children[i], low_key, high_key, result)

            # Visit internal key i.
            key = node.keys[i]
            rid = node.rids[i]

            if low_key <= key <= high_key:
                result.append((key, rid))

        # Traverse rightmost child.
        self._range_query_node(node.children[-1], low_key, high_key, result)

    def validate(self):
        """
        Validate B* tree structural properties.

        Returns:
            True if valid.

        Raises:
            ValueError if invalid.
        """

        leaf_depths = []

        self._validate_node(
            node=self.root,
            is_root=True,
            depth=0,
            leaf_depths=leaf_depths,
            min_key=None,
            max_key=None,
        )

        if len(set(leaf_depths)) > 1:
            raise ValueError(f"Leaves are at different depths: {leaf_depths}")

        return True

    def _validate_node(
        self,
        node,
        is_root,
        depth,
        leaf_depths,
        min_key,
        max_key,
    ):
        """
        Recursively validate a B* tree node.
        """

        # 1. keys and rids must match in length.
        if len(node.keys) != len(node.rids):
            raise ValueError(
                f"keys/rids length mismatch: keys={len(node.keys)}, rids={len(node.rids)}"
            )

        # 2. keys must be strictly sorted.
        for i in range(len(node.keys) - 1):
            if node.keys[i] >= node.keys[i + 1]:
                raise ValueError(f"Keys are not strictly sorted: {node.keys}")

        # 3. node should not exceed max_keys.
        if len(node.keys) > self.max_keys:
            raise ValueError(
                f"Node has too many keys: {len(node.keys)} > {self.max_keys}"
            )

        # 4. non-root node should satisfy minimum occupancy.
        if not is_root and len(node.keys) < self.min_keys:
            raise ValueError(
                f"Non-root node has too few keys: {len(node.keys)} < {self.min_keys}"
            )

        # 5. keys must respect parent boundary.
        for key in node.keys:
            if min_key is not None and key <= min_key:
                raise ValueError(f"Key {key} violates min bound {min_key}")

            if max_key is not None and key >= max_key:
                raise ValueError(f"Key {key} violates max bound {max_key}")

        # 6. leaf node validation.
        if node.is_leaf:
            if len(node.children) != 0:
                raise ValueError("Leaf node should not have children")

            leaf_depths.append(depth)
            return

        # 7. internal node validation.
        if len(node.children) != len(node.keys) + 1:
            raise ValueError(
                f"Invalid children count: children={len(node.children)}, keys={len(node.keys)}"
            )

        for i, child in enumerate(node.children):
            child_min = min_key
            child_max = max_key

            if i == 0:
                child_max = node.keys[0]
            elif i == len(node.children) - 1:
                child_min = node.keys[-1]
            else:
                child_min = node.keys[i - 1]
                child_max = node.keys[i]

            self._validate_node(
                node=child,
                is_root=False,
                depth=depth + 1,
                leaf_depths=leaf_depths,
                min_key=child_min,
                max_key=child_max,
            )