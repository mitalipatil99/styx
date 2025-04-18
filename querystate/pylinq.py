from py_linq import Enumerable



def main():

    data = [
        {"id": 1, "name": "Alice", "age": 25},
        {"id": 2, "name": "Bob", "age": 30},
        {"id": 3, "name": "Charlie", "age": 35},
        {"id": 4, "name": "Diana", "age": 40}
    ]

    enumerable_data = Enumerable(data)
    filtered_data = enumerable_data.where(lambda x:x["age"]>30) #range query test.
    # print(filtered_data)

    marks1 = Enumerable([{'course': 'Chemistry', 'mark': 90}, {'course': 'Biology', 'mark': 85}])
    marks2 = Enumerable([{'course': 'Chemistry', 'mark': 65}, {'course': 'Computer Science', 'mark': 96}])
    common_courses = marks2.intersect(marks1, lambda c: c['course'])
    print("Common courses:", list(common_courses))  #why is the intersection only adding on object
    #custom code
    common_courses = marks1.where(lambda x: any(x['course'] == y['course'] for y in marks2))
    print("Common courses with custom code:", list(common_courses)) #????????????

    filtered_data = enumerable_data.count(lambda x: x["age"] >=30)  # count query test.
    print(filtered_data)

    locations = [
        ('Scotland', 'Edinburgh', 'Branch1', 20000),
        ('Scotland', 'Glasgow', 'Branch1', 12500),
        ('Scotland', 'Glasgow', 'Branch2', 12000),
        ('Wales', 'Cardiff', 'Branch1', 29700),
        ('Wales', 'Cardiff', 'Branch2', 30000),
        ('Wales', 'Bangor', 'Branch1', 12800),
        ('England', 'London', 'Branch1', 90000),
        ('England', 'London', 'Branch2', 80000),
        ('England', 'London', 'Branch3', 70000),
        ('England', 'Manchester', 'Branch1', 45600),
        ('England', 'Manchester', 'Branch2', 50000),
        ('England', 'Liverpool', 'Branch1', 29700),
        ('England', 'Liverpool', 'Branch2', 25000)
    ]
    print(Enumerable(locations).group_by(key_names=['city'], key=lambda x: [x[1]]).to_list())



if __name__ == "__main__":
    main()


#check dict to pandas query langauge
#check alternatives.