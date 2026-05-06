import math

class BTreeNode:
    """
    A node in a B-tree.

    keys[i] corresponds to rids[i].
    children are used only when this node is not a leaf.
    """

    def __init__(self, is_leaf=True):
        self.keys = []
        self.rids = []
        self.children = []
        self.is_leaf = is_leaf


class BTree:
    """
    B-tree index structure.

    d is interpreted as the minimum degree:
    - max_keys = 2d - 1
    - min_keys = d - 1 for non-root nodes
    """

    def __init__(self, d):
        self.d = d
        self.max_children = d
        self.max_keys = d - 1
        self.min_children = math.ceil(d / 2)
        self.min_keys = self.min_children - 1
        self.num_splits = 0
        self.root = BTreeNode(is_leaf=True)
    
    def insert(self, key, rid):
        """
        Insert a key-RID pair into the B-tree using fan-out order definition.

        If a node overflows, split is propagated upward.
        """
        promoted = self._insert_recursive(self.root, key, rid)

        if promoted is not None:
            promoted_key, promoted_rid, right_node = promoted

            old_root = self.root
            new_root = BTreeNode(is_leaf=False)

            new_root.keys = [promoted_key]
            new_root.rids = [promoted_rid]
            new_root.children = [old_root, right_node]

            self.root = new_root
    def _insert_recursive(self, node, key, rid):
        """
        Insert into subtree rooted at node.

        Returns:
            None if no split occurs.
            (promoted_key, promoted_rid, right_node) if node is split.
        """

        if node.is_leaf:
            i = len(node.keys) - 1

            node.keys.append(None)
            node.rids.append(None)

            while i >= 0 and key < node.keys[i]:
                node.keys[i + 1] = node.keys[i]
                node.rids[i + 1] = node.rids[i]
                i -= 1

            node.keys[i + 1] = key
            node.rids[i + 1] = rid

            if len(node.keys) > self.max_keys:
                return self._split_overflow_node(node)

            return None

        i = 0
        while i < len(node.keys) and key > node.keys[i]:
            i += 1

        promoted = self._insert_recursive(node.children[i], key, rid)

        if promoted is not None:
            promoted_key, promoted_rid, right_node = promoted

            node.keys.insert(i, promoted_key)
            node.rids.insert(i, promoted_rid)
            node.children.insert(i + 1, right_node)

            if len(node.keys) > self.max_keys:
                return self._split_overflow_node(node)

        return None
    
    def search(self, key):
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
    
    def delete(self, key):
        
        if self.search(key) is None:
            return False
        deleted = self._delete_node(self.root, key)
        if not self.root.is_leaf and len(self.root.keys) == 0:
            self.root = self.root.children[0]

        return deleted

    def _delete_node(self, node, key):
        """
        Delete key from the subtree rooted at node.

        This version supports:
        - deletion from leaf nodes
        - deletion from internal nodes using predecessor
          when the left child has more than min_keys
        """

        i = 0
        while i < len(node.keys) and key > node.keys[i]:
            i += 1

        # Case 1: key is found in this node
        if i < len(node.keys) and key == node.keys[i]:
            if node.is_leaf:
                node.keys.pop(i)
                node.rids.pop(i)
                return True

            return self._delete_from_internal_node(node, i)

        # Case 2: key is not found in this node
        if node.is_leaf:
            return False
        
        if len(node.children[i].keys) == self.min_keys:
            i = self._fill_child_before_delete(node, i)

        deleted = self._delete_node(node.children[i], key)

        if len(node.children[i].keys) > self.max_keys:
            promoted_key, promoted_rid, right_node = self._split_overflow_node(node.children[i])
            node.keys.insert(i, promoted_key)
            node.rids.insert(i, promoted_rid)
            node.children.insert(i + 1, right_node)

        return deleted

    def _delete_from_internal_node(self, node, key_index):

        key = node.keys[key_index]
        left_child = node.children[key_index]
        right_child = node.children[key_index + 1]

        if len(left_child.keys) > self.min_keys:
            pred_key, pred_rid = self._get_predecessor(left_child)

            node.keys[key_index] = pred_key
            node.rids[key_index] = pred_rid

            return self._delete_node(left_child, pred_key)

        if len(right_child.keys) > self.min_keys:
            succ_key, succ_rid = self._get_successor(right_child)

            node.keys[key_index] = succ_key
            node.rids[key_index] = succ_rid

            return self._delete_node(right_child, succ_key)

        merged_child = self._merge_children(node, key_index)
        deleted = self._delete_node(merged_child, key)
    
        if len(merged_child.keys) > self.max_keys:
            promoted_key, promoted_rid, right_node = self._split_overflow_node(merged_child)
            node.keys.insert(key_index, promoted_key)
            node.rids.insert(key_index, promoted_rid)
            node.children.insert(key_index + 1, right_node)

        return deleted
                
    def _delete_from_leaf(self, node, key):
        for i in range(len(node.keys)):
            if node.keys[i] == key:
                node.keys.pop(i)
                node.rids.pop(i)
                return True

        return False
    
    def _fill_child_before_delete(self, parent, child_index):
        """
        Ensure that parent.children[child_index] has more than min_keys
        before descending into it during deletion.

        Current supported case:
        - borrow from right sibling if possible.

        Returns:
            The child index to continue deletion.
        """
        if (
            child_index > 0
            and len(parent.children[child_index - 1].keys) > self.min_keys
        ):
            self._borrow_from_prev(parent, child_index)
            return child_index
        
        if (
            child_index + 1 < len(parent.children)
            and len(parent.children[child_index + 1].keys) > self.min_keys
        ):
            self._borrow_from_next(parent, child_index)
            return child_index

        if child_index + 1 < len(parent.children):
            self._merge_children(parent, child_index)
            return child_index

        self._merge_children(parent, child_index - 1)
        return child_index - 1
    
    def _borrow_from_prev(self, parent, child_index):
        """
        Borrow one key from the left sibling.

        parent.children[child_index] is the child that needs one more key.
        parent.children[child_index - 1] is the left sibling.

        For B-tree:
        - parent separator key moves down to child
        - left sibling's last key moves up to parent
        """

        child = parent.children[child_index]
        left_sibling = parent.children[child_index - 1]

        # Move parent separator down to the front of child.
        child.keys.insert(0, parent.keys[child_index - 1])
        child.rids.insert(0, parent.rids[child_index - 1])

        # Move left sibling's last key up to parent.
        parent.keys[child_index - 1] = left_sibling.keys.pop()
        parent.rids[child_index - 1] = left_sibling.rids.pop()

        # If internal nodes, move the last child pointer of left sibling.
        if not child.is_leaf:
            child.children.insert(0, left_sibling.children.pop())

    def _borrow_from_next(self, parent, child_index):
        """
        Borrow one key from the right sibling.

        parent.children[child_index] is the child that needs one more key.
        parent.children[child_index + 1] is the right sibling.

        For B-tree:
        - parent separator key moves down to child
        - right sibling's first key moves up to parent
        """

        child = parent.children[child_index]
        right_sibling = parent.children[child_index + 1]

        # Move parent separator down to child.
        child.keys.append(parent.keys[child_index])
        child.rids.append(parent.rids[child_index])

        # Move right sibling's first key up to parent.
        parent.keys[child_index] = right_sibling.keys.pop(0)
        parent.rids[child_index] = right_sibling.rids.pop(0)

        # If internal nodes, move the first child pointer of right sibling.
        if not child.is_leaf:
            child.children.append(right_sibling.children.pop(0))

    def _get_predecessor(self, node):
        current = node

        while not current.is_leaf:
            current = current.children[-1]

        return current.keys[-1], current.rids[-1]

    def _get_successor(self, node):
        """
        Return the smallest key-RID pair in the subtree rooted at node.
        """

        current = node

        while not current.is_leaf:
            current = current.children[0]

        return current.keys[0], current.rids[0]

    def _merge_children(self, parent, key_index):
        """
        Merge parent.keys[key_index] and its two adjacent children.

        Before:
            parent.keys[key_index] separates left_child and right_child.

        After:
            left_child contains:
                left_child keys + separator key + right_child keys

            The separator key and right_child are removed from parent.

        Returns:
            The merged child.
        """

        left_child = parent.children[key_index]
        right_child = parent.children[key_index + 1]

        separator_key = parent.keys.pop(key_index)
        separator_rid = parent.rids.pop(key_index)

        left_child.keys.append(separator_key)
        left_child.rids.append(separator_rid)

        left_child.keys.extend(right_child.keys)
        left_child.rids.extend(right_child.rids)

        if not left_child.is_leaf:
            left_child.children.extend(right_child.children)

        parent.children.pop(key_index + 1)

        return left_child

    def _split_overflow_node(self, node):
        """
        Split an overflow node.

        This implementation assumes:
        - d = maximum fan-out
        - max_keys = d - 1
        - overflow occurs when len(node.keys) == d

        Returns:
            promoted_key, promoted_rid, right_node
        """

        median_index = len(node.keys) // 2

        promoted_key = node.keys[median_index]
        promoted_rid = node.rids[median_index]

        right_node = BTreeNode(is_leaf=node.is_leaf)

        right_node.keys = node.keys[median_index + 1:]
        right_node.rids = node.rids[median_index + 1:]

        left_keys = node.keys[:median_index]
        left_rids = node.rids[:median_index]

        if not node.is_leaf:
            right_node.children = node.children[median_index + 1:]
            node.children = node.children[:median_index + 1]

        node.keys = left_keys
        node.rids = left_rids

        self.num_splits += 1

        return promoted_key, promoted_rid, right_node
                

    def validate(self):
        """
        Validate basic B-tree structural properties.

        Returns:
            True if the tree is valid.
        Raises:
            ValueError if any structural property is violated.
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
    
    def _validate_node(self, node, is_root, depth, leaf_depths, min_key, max_key):
        """
        Recursively validate a B-tree node.
        """

        # 1. keys and rids must have same length
        if len(node.keys) != len(node.rids):
            raise ValueError(
                f"keys/rids length mismatch: keys={len(node.keys)}, rids={len(node.rids)}"
            )

        # 2. keys must be sorted
        for i in range(len(node.keys) - 1):
            if node.keys[i] >= node.keys[i + 1]:
                raise ValueError(f"Keys are not strictly sorted: {node.keys}")

        # 3. node must not exceed max_keys
        if len(node.keys) > self.max_keys:
            raise ValueError(
                f"Node has too many keys: {len(node.keys)} > {self.max_keys}"
            )

        # 4. non-root nodes must have at least min_keys
        if not is_root and len(node.keys) < self.min_keys:
            raise ValueError(
                f"Non-root node has too few keys: {len(node.keys)} < {self.min_keys}"
            )

        # 5. keys must be within allowed range
        for key in node.keys:
            if min_key is not None and key <= min_key:
                raise ValueError(f"Key {key} violates min bound {min_key}")
            if max_key is not None and key >= max_key:
                raise ValueError(f"Key {key} violates max bound {max_key}")

        # 6. leaf node check
        if node.is_leaf:
            if len(node.children) != 0:
                raise ValueError("Leaf node should not have children")
            leaf_depths.append(depth)
            return

        # 7. internal node must have children count = keys count + 1
        if len(node.children) != len(node.keys) + 1:
            raise ValueError(
                f"Invalid children count: children={len(node.children)}, keys={len(node.keys)}"
            )

        # 8. recursively validate children with updated key ranges
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
