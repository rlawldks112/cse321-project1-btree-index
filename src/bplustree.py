import math


class BPlusTreeNode:
    """
    A node in a B+ tree.

    Internal node:
        - stores separator keys
        - stores child pointers
        - does not store RIDs

    Leaf node:
        - stores actual keys
        - stores RIDs
        - stores next pointer for range scan
    """

    def __init__(self, is_leaf=True):
        self.is_leaf = is_leaf
        self.keys = []
        self.children = []
        self.rids = []
        self.next = None


class BPlusTree:
    """
    B+ tree index structure.

    In this implementation:
    - d is interpreted as the maximum fan-out order.
    - max_keys = d - 1
    - min_keys = ceil(d / 2) - 1
    """

    def __init__(self, d):
        if d < 3:
            raise ValueError("B+ tree order d must be at least 3")

        self.d = d
        self.max_keys = d - 1
        self.min_keys = math.ceil(d / 2) - 1
        self.root = BPlusTreeNode(is_leaf=True)
        self.num_splits = 0

    def _find_leaf(self, key):
        """
        Find the leaf node where the given key should exist.

        B+ tree search must always descend to a leaf.
        """

        current = self.root

        while not current.is_leaf:
            i = 0

            while i < len(current.keys) and key >= current.keys[i]:
                i += 1

            current = current.children[i]

        return current
    
    def search(self, key):
        """
        Search for a key in the B+ tree.

        Returns:
            RID if found in a leaf node.
            None otherwise.
        """

        leaf = self._find_leaf(key)

        for i, existing_key in enumerate(leaf.keys):
            if existing_key == key:
                return leaf.rids[i]

        return None

    def insert(self, key, rid):
        """
        Insert a key-RID pair into the B+ tree.

        Supports:
        - insertion into leaf
        - leaf split
        - internal node split
        - root split
        """

        leaf, path = self._find_leaf_with_path(key)
        self._insert_into_leaf(leaf, key, rid)

        if len(leaf.keys) <= self.max_keys:
            return

        separator_key, right_node = self._split_leaf(leaf)

        # If the old root was a leaf, create a new root.
        if not path:
            old_root = self.root
            new_root = BPlusTreeNode(is_leaf=False)

            new_root.keys = [separator_key]
            new_root.children = [old_root, right_node]
            new_root.rids = []

            self.root = new_root
            return

        # Propagate split upward.
        while path:
            parent, child_index = path.pop()

            parent.keys.insert(child_index, separator_key)
            parent.children.insert(child_index + 1, right_node)
            parent.rids = []

            if len(parent.keys) <= self.max_keys:
                return

            separator_key, right_node = self._split_internal(parent)

            # If parent was the root and it overflowed, create a new root.
            if not path:
                old_root = self.root
                new_root = BPlusTreeNode(is_leaf=False)

                new_root.keys = [separator_key]
                new_root.children = [old_root, right_node]
                new_root.rids = []

                self.root = new_root
                return    

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

    def _split_leaf(self, leaf):
        """
        Split an overflow leaf node.

        In B+ tree leaf split:
        - actual key-RID pairs remain in leaf nodes
        - the first key of the right leaf is copied to the parent
        - leaf linked list must be updated

        Returns:
            separator_key, right_leaf
        """

        split_index = len(leaf.keys) // 2

        right_leaf = BPlusTreeNode(is_leaf=True)

        right_leaf.keys = leaf.keys[split_index:]
        right_leaf.rids = leaf.rids[split_index:]

        leaf.keys = leaf.keys[:split_index]
        leaf.rids = leaf.rids[:split_index]

        right_leaf.next = leaf.next
        leaf.next = right_leaf

        separator_key = right_leaf.keys[0]

        self.num_splits += 1

        return separator_key, right_leaf
    
    def _find_leaf_with_path(self, key):
        """
        Find the leaf node where the key should exist.

        Returns:
            leaf: target leaf node
            path: list of (parent_node, child_index) pairs

        path stores how we reached the leaf.
        The last item in path is the parent of the leaf.
        """

        current = self.root
        path = []

        while not current.is_leaf:
            i = 0

            while i < len(current.keys) and key >= current.keys[i]:
                i += 1

            path.append((current, i))
            current = current.children[i]

        return current, path
    
    def _split_internal(self, node):
        """
        Split an overflow internal node.

        In B+ tree internal split:
        - the middle separator key is promoted to the parent
        - the promoted key is removed from the split children
        - internal nodes do not store RIDs

        Returns:
            promoted_key, right_node
        """

        median_index = len(node.keys) // 2

        promoted_key = node.keys[median_index]

        right_node = BPlusTreeNode(is_leaf=False)

        right_node.keys = node.keys[median_index + 1:]
        right_node.children = node.children[median_index + 1:]
        right_node.rids = []

        node.keys = node.keys[:median_index]
        node.children = node.children[:median_index + 1]
        node.rids = []

        self.num_splits += 1

        return promoted_key, right_node
    
    def validate(self):
        """
        Validate B+ tree structural properties.

        Returns:
            True if valid.
        Raises:
            ValueError if any property is violated.
        """

        leaf_depths = []
        leaves_in_tree_order = []

        self._validate_node(
            node=self.root,
            is_root=True,
            depth=0,
            leaf_depths=leaf_depths,
            leaves_in_tree_order=leaves_in_tree_order,
            min_key=None,
            max_key=None,
        )

        if len(set(leaf_depths)) > 1:
            raise ValueError(f"Leaves are at different depths: {leaf_depths}")

        self._validate_leaf_links(leaves_in_tree_order)

        return True
    
    def _validate_node(
        self,
        node,
        is_root,
        depth,
        leaf_depths,
        leaves_in_tree_order,
        min_key,
        max_key,
    ):
        """
        Recursively validate a B+ tree node.
        """

        # 1. keys must be sorted
        for i in range(len(node.keys) - 1):
            if node.keys[i] >= node.keys[i + 1]:
                raise ValueError(f"Keys are not strictly sorted: {node.keys}")

        # 2. node must not exceed max_keys
        if len(node.keys) > self.max_keys:
            raise ValueError(
                f"Node has too many keys: {len(node.keys)} > {self.max_keys}"
            )

        # 3. non-root nodes must have at least min_keys
        if not is_root and len(node.keys) < self.min_keys:
            raise ValueError(
                f"Non-root node has too few keys: {len(node.keys)} < {self.min_keys}"
            )

        # 4. keys must be within allowed range
        for key in node.keys:
            if min_key is not None and key < min_key:
                raise ValueError(f"Key {key} violates min bound {min_key}")
            if max_key is not None and key >= max_key:
                raise ValueError(f"Key {key} violates max bound {max_key}")

        # 5. leaf node validation
        if node.is_leaf:
            if len(node.children) != 0:
                raise ValueError("Leaf node should not have children")

            if len(node.keys) != len(node.rids):
                raise ValueError(
                    f"Leaf keys/rids length mismatch: "
                    f"keys={len(node.keys)}, rids={len(node.rids)}"
                )

            leaf_depths.append(depth)
            leaves_in_tree_order.append(node)
            return

        # 6. internal node validation
        if len(node.rids) != 0:
            raise ValueError("Internal node should not store RIDs")

        if len(node.children) != len(node.keys) + 1:
            raise ValueError(
                f"Invalid children count: "
                f"children={len(node.children)}, keys={len(node.keys)}"
            )

        # 7. recursively validate children
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
                leaves_in_tree_order=leaves_in_tree_order,
                min_key=child_min,
                max_key=child_max,
            )

    def _validate_leaf_links(self, leaves_in_tree_order):
        """
        Validate that leaf next pointers follow the tree-order leaf sequence.
        """

        if not leaves_in_tree_order:
            return

        for i in range(len(leaves_in_tree_order) - 1):
            current_leaf = leaves_in_tree_order[i]
            expected_next = leaves_in_tree_order[i + 1]

            if current_leaf.next is not expected_next:
                raise ValueError(
                    f"Invalid leaf link at index {i}: "
                    f"current keys={current_leaf.keys}, "
                    f"expected next keys={expected_next.keys}"
                )

            if current_leaf.keys and expected_next.keys:
                if current_leaf.keys[-1] > expected_next.keys[0]:
                    raise ValueError(
                        f"Leaf link order violation: "
                        f"{current_leaf.keys[-1]} > {expected_next.keys[0]}"
                    )

        last_leaf = leaves_in_tree_order[-1]

        if last_leaf.next is not None:
            raise ValueError("Last leaf next pointer should be None")
        
    def range_query(self, low_key, high_key):
        """
        Return all (key, rid) pairs such that low_key <= key <= high_key.

        B+ tree range query:
        1. Find the leaf where low_key should be located.
        2. Scan keys in that leaf.
        3. Follow leaf.next pointers until keys exceed high_key.
        """

        if low_key > high_key:
            return []

        result = []

        current = self._find_leaf(low_key)

        while current is not None:
            for key, rid in zip(current.keys, current.rids):
                if key < low_key:
                    continue

                if key > high_key:
                    return result

                result.append((key, rid))

            current = current.next

        return result       

    def delete(self, key):
        """
        Delete a key from the B+ tree.

        Current version:
        - deletes key-RID pair from the target leaf
        - if leaf underflows, borrows from left sibling when possible
        - does not yet handle borrow from right sibling or merge

        Returns:
            True if deleted, False otherwise.

        1. leaf에서 key 삭제
        2. leaf underflow 처리
        3. leaf merge 때문에 parent internal node가 underflow됐는지 확인
        4. underflow된 internal node를 borrow 또는 merge로 복구
        5. root가 비면 root shrink
        """

        leaf, path = self._find_leaf_with_path(key)

        deleted = self._delete_from_leaf(leaf, key)

        if not deleted:
            return False

        # If root is a leaf, no minimum occupancy constraint is needed.
        if leaf is self.root:
            return True

        if len(leaf.keys) < self.min_keys:
            parent, child_index = path[-1]
            self._handle_leaf_underflow(parent, child_index)

        for level in range(len(path) - 2, -1, -1):
            parent_node, child_index = path[level]

            if child_index >= len(parent_node.children):
                child_index = len(parent_node.children) - 1

            child_node = parent_node.children[child_index]

            if (
                not child_node.is_leaf
                and child_node is not self.root
                and len(child_node.keys) < self.min_keys
            ):
                self._handle_internal_underflow(parent_node, child_index)

        # Root shrink.
        while not self.root.is_leaf and len(self.root.keys) == 0:
            self.root = self.root.children[0]

        return True    

    def _delete_from_leaf(self, leaf, key):
        """
        Delete key-RID pair from a leaf node.

        Returns:
            True if the key was deleted.
            False if the key was not found.
        """

        for i, existing_key in enumerate(leaf.keys):
            if existing_key == key:
                leaf.keys.pop(i)
                leaf.rids.pop(i)
                return True

        return False

    def _handle_leaf_underflow(self, parent, child_index):
        """
        Handle underflow in a leaf child of parent.

        Current supported case:
        - borrow from left sibling if possible

        1. 왼쪽 sibling이 빌려줄 수 있으면 borrow from prev
        2. 아니면 오른쪽 sibling이 빌려줄 수 있으면 borrow from next
        3. 둘 다 안 되면 merge
        4. 가능하면 child + right sibling을 merge
        5. child가 가장 오른쪽이면 left sibling + child를 merge
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
        Handle underflow in an internal child of parent.

        Supported cases:
        - borrow from left internal sibling if possible
        - borrow from right internal sibling if possible
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

        For B+ tree leaf borrowing:
        - move the last key-RID pair of the left sibling
          to the front of the underflowed leaf
        - update parent separator so search routes correctly
        """

        child = parent.children[child_index]
        left_sibling = parent.children[child_index - 1]

        borrowed_key = left_sibling.keys.pop()
        borrowed_rid = left_sibling.rids.pop()

        child.keys.insert(0, borrowed_key)
        child.rids.insert(0, borrowed_rid)

        # The separator should guide searches for child to this child.
        parent.keys[child_index - 1] = child.keys[0]

    def _borrow_leaf_from_next(self, parent, child_index):
        """
        Borrow one key-RID pair from the right leaf sibling.

        For B+ tree leaf borrowing:
        - move the first key-RID pair of the right sibling
          to the end of the underflowed leaf
        - update parent separator so search routes correctly
        """

        child = parent.children[child_index]
        right_sibling = parent.children[child_index + 1]

        borrowed_key = right_sibling.keys.pop(0)
        borrowed_rid = right_sibling.rids.pop(0)

        child.keys.append(borrowed_key)
        child.rids.append(borrowed_rid)

        # After borrowing, the right sibling's first key changed.
        # Parent separator should represent the first key of the right sibling.
        parent.keys[child_index] = right_sibling.keys[0]

    def _borrow_internal_from_prev(self, parent, child_index):
        """
        Borrow one separator and one child pointer from the left internal sibling.
        """

        child = parent.children[child_index]
        left_sibling = parent.children[child_index - 1]

        child.keys.insert(0, parent.keys[child_index - 1])
        child.children.insert(0, left_sibling.children.pop())

        parent.keys[child_index - 1] = left_sibling.keys.pop()

        child.rids = []
        left_sibling.rids = []
        parent.rids = []

    def _borrow_internal_from_next(self, parent, child_index):
        """
        Borrow one separator and one child pointer from the right internal sibling.
        """

        child = parent.children[child_index]
        right_sibling = parent.children[child_index + 1]

        child.keys.append(parent.keys[child_index])
        child.children.append(right_sibling.children.pop(0))

        parent.keys[child_index] = right_sibling.keys.pop(0)

        child.rids = []
        right_sibling.rids = []
        parent.rids = []

    def _merge_leaf_with_next(self, parent, left_index):
        """
        Merge a leaf child with its right leaf sibling.

        parent.children[left_index] and parent.children[left_index + 1]
        must both be leaf nodes.

        After merge:
        - left leaf contains all key-RID pairs
        - right leaf is removed from parent.children
        - separator key between them is removed from parent.keys
        - leaf linked list is updated
        """

        left_leaf = parent.children[left_index]
        right_leaf = parent.children[left_index + 1]

        left_leaf.keys.extend(right_leaf.keys)
        left_leaf.rids.extend(right_leaf.rids)

        left_leaf.next = right_leaf.next

        parent.keys.pop(left_index)
        parent.children.pop(left_index + 1)

        parent.rids = []

    def _merge_internal_with_next(self, parent, left_index):
        """
        Merge an internal child with its right internal sibling.

        For internal merge:
        - parent separator key moves down into the merged internal node
        - right sibling's keys and children are appended
        - right sibling is removed from parent.children
        """

        left_child = parent.children[left_index]
        right_child = parent.children[left_index + 1]

        separator_key = parent.keys.pop(left_index)

        left_child.keys.append(separator_key)
        left_child.keys.extend(right_child.keys)

        left_child.children.extend(right_child.children)

        parent.children.pop(left_index + 1)

        left_child.rids = []
        right_child.rids = []
        parent.rids = []

