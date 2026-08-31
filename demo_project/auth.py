def calculate_average(total_marks, number_of_subjects):
    return total_marks / number_of_subjects

def get_student(name, total_marks, number_of_subjects):
    average = calculate_average(
        total_marks,
        number_of_subjects
    )
    return {
        "name": name,
        "total_marks": total_marks,
        "average": average,
    }

def get_result(student):
    if student["average"] >= 40:
        return "PASS"
    return "FAIL"

def print_report(student):
    print("Student:", student["name"])
    print("Total Marks:", student["total_marks"])
    print("Average:", student["average"])
    print("Result:", get_result(student))

if __name__ == "__main__":
    student = get_student(
        "Mahesh",
        0,
        0
    )
    print_report(student)
