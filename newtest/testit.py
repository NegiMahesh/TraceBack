def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)


def get_student_data():
    students = {
        "Mahesh": [85, 90, 78],
        "Rahul": [72, 88, 91],
        "Aman": []
    }

    for name, marks in students.items():
        average = calculate_average(marks)
        print(f"{name}'s average: {average:.2f}")


def main():
    print("Starting student grade analyzer...")
    get_student_data()


if __name__ == "__main__":
    main()