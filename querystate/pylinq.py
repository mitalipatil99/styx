from py_linq import Enumerable


class LinqStateStore:
    def __init__(self):
        """
        Initializes the LinqStateStore.
        """
        self.state_store = {}
        self.queryable_state = None

    def makeflatMap(self, state_store):
        """
        Initialize the LINQ wrapper for the state store.

        :param state_store: A dictionary containing operator-partition-key-value data.
        """
        self.state_store = state_store
        # Flatten state_store dictionary items into a structure compatible with Enumerable
        flat_state = [
            {'operator': key[0], 'partition': key[1], 'key': k, 'value': v}
            for key, data in state_store.items()
            for k, v in data.items()
        ]
        # Create a LINQ-compatible enumerable object
        self.queryable_state = Enumerable(flat_state)

    def __iter__(self):
        """
        Make the state store directly iterable.
        """
        if not self.queryable_state:
            raise ValueError("Queryable state not initialized. Call makeflatMap() first.")
        return iter(self.queryable_state)

    def __repr__(self):
        """
        String representation of the LinqStateStore.
        """
        return f"LinqStateStore({self.queryable_state})"

    def get_order_aggregates(self):
        """
        Gets aggregated statistics for orders.
        Returns quantity and amount aggregates grouped by order.
        """
        orders = self.queryable_state.where(lambda x: x['operator'] == 'order')
        order_per_partition_stats = orders.group_by(key_names=["partitionID"], key=lambda x: x['partition']).select(
            lambda g: {
                'partition': {'partitionID': g.key.partitionID,
                              'sum_qty': sum(sum(x['value']['items'].values()) for x in g),
                              # total quantity of items per partition
                              'sum_amount': sum(x['value']['total_cost'] for x in g),
                              # total cost of items per partition
                              'count_order': len(g)  # total order per partition.
                              }}).to_list()
        print("Per partition statistics:")
        print(order_per_partition_stats)

        total_stats = {
            'total_sum_qty': sum(stat['partition']['sum_qty'] for stat in order_per_partition_stats),  #total quanitities of all partition
            'total_sum_amount': sum(stat['partition']['sum_amount'] for stat in order_per_partition_stats), #total amount of all orders for all partition
            'total_count_order': sum(stat['partition']['count_order'] for stat in order_per_partition_stats)
        }
        print("\nTotal statistics across all partitions:")
        print(total_stats)

    def get_unpaid_expensive_orders(self):
        """
        Gets all orders that are unpaid and have total_cost >= 100
        """
        print(self.queryable_state.where(
            lambda x: x['operator'] == 'order' and
                      not x['value']['paid'] and
                      x['value']['total_cost'] >= 100
        ).to_list())



# Example usage
if __name__ == "__main__":
    # Example state_store data
    state_store = {
        ('order', 2): {
            686: {'paid': True, 'items': {497: 1, 352: 4}, 'user_id': 928, 'total_cost': 2},
            118: {'paid': False, 'items': {705: 1, 285: 1}, 'user_id': 173, 'total_cost': 2},
            438: {'paid': False, 'items': {313: 3, 352: 1}, 'user_id': 928, 'total_cost': 100},
            101: {'paid': True, 'items': {980: 1, 285: 2}, 'user_id': 173, 'total_cost': 2}
        },
        ('stock', 1): {497: {'stock': 9999, 'price': 1}, 705: {'stock': 9999, 'price': 1},
                       285: {'stock': 9999, 'price': 1}, 225: {'stock': 9999, 'price': 1},
                       249: {'stock': 9998, 'price': 1}, 125: {'stock': 9997, 'price': 1},
                       537: {'stock': 9999, 'price': 1}, 989: {'stock': 9999, 'price': 1},
                       425: {'stock': 9999, 'price': 1}, 961: {'stock': 9999, 'price': 1},
                       757: {'stock': 9998, 'price': 1}, 477: {'stock': 9998, 'price': 1},
                       313: {'stock': 9999, 'price': 1}, 101: {'stock': 9999, 'price': 1},
                       61: {'stock': 9999, 'price': 1}, 825: {'stock': 9999, 'price': 1},
                       765: {'stock': 9999, 'price': 1}
        },
        ('payment', 2): {
            118: {'credit': 998},
            438: {'credit': 996},
        },
        ('order', 0): {
            34588: {'paid': True, 'items': {48915: 3, 92454: 1}, 'user_id': 94127, 'total_cost': 2},
            45716: {'paid': False, 'items': {30063: 1, 84492: 1}, 'user_id': 34356, 'total_cost': 1000}
        },
        ('payment', 1): {
            69957: {'credit': 999998},
            37685: {'credit': 999998},
            80737: {'credit': 999998},
            7993: {'credit': 999998}
        }
    }

    linq_state_store = LinqStateStore()
    linq_state_store.makeflatMap(state_store)

    # Example LINQ query for order aggregates
    linq_state_store.get_order_aggregates()

    # Get unpaid expensive orders
    linq_state_store.get_unpaid_expensive_orders()

