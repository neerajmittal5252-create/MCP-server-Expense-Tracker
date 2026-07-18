from fastmcp import FastMCP
import os
import uuid
from db import get_conn

DATABASE_URL = os.environ["DATABASE_URL"]
mcp=FastMCP("employee-server")

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                CREATE EXTENSION IF NOT EXISTS "pgcrypto";
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS departments (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    department_name VARCHAR(100) UNIQUE NOT NULL,
                    manager VARCHAR(100),
                    budget NUMERIC(12,2),
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS employees (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(100) NOT NULL,
                    age INT CHECK (age >= 18),
                    department UUID REFERENCES departments(id) ON DELETE SET NULL,
                    salary NUMERIC(10,2) NOT NULL,
                    joining_date DATE,
                    phone_no VARCHAR(15) NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

        conn.commit()

init_db()

@mcp.tool()
def add_employee(name: str,age: int,department,salary: float,joining_date: str,phone_no: str):
    """Add a new employee to the database."""
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                "INSERT INTO employees(name, age, department,salary,joining_date,phone_no) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                (name, age, department,salary,joining_date,phone_no)
            )
            new_id=cur.fetchone()[0]
        c.commit() 
        return {"status":"ok","id":new_id}
    

@mcp.tool()
def update_employee(employee_id: str,name: str = None,age: int = None,department: str = None,salary: float = None,joining_date: str = None,phone_no: str = None):
    """Update an employee's details."""
    update=[]
    value=[]
    if name is not None:
        update.append("name=%s")
        value.append(name)
    if age is not None:
        update.append("age=%s")
        value.append(age)
    if department is not None:
        update.append("department=%s")
        value.append(department)
    if salary is not None:
        update.append("salary=%s")
        value.append(salary)
    if joining_date is not None:
        update.append("joining_date=%s")
        value.append(joining_date)
    if phone_no is not None:
        update.append("phone_no=%s")
        value.append(phone_no)
    if not update:
        return {"status": "error","message": "No fields to update."}
    
    value.append(employee_id)
    query=f"""
        UPDATE employees
        SET {', '.join(update)}
        where id=%s
        RETURNING id;
""" 
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, value)
            row = cur.fetchone()
            if row is None:
                return {
                    "status": "error",
                    "message": "Employee not found."
                }
        conn.commit()
    return {
        "status": "ok",
        "id": str(row[0])
    }

@mcp.tool()
def delete_employee(phone_no:str):
    """Delete employee's data"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM employees
                WHERE phone_no=%s
                RETURNING id
""",(phone_no,))
            row=cur.fetchone()
            if row is None:
                return{
                    "status":"error",
                    "message":"Employee not found"
                }
        conn.commit()
    return {
        "status": "ok",
        "id": str(row[0])
    }
@mcp.tool()
def add_department(department_name: str, manager: str = None, budget: float = None):
    """Add a new department to the database."""
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                "INSERT INTO departments(department_name, manager, budget) VALUES (%s,%s,%s) RETURNING id",
                (department_name, manager, budget)
            )
            new_id = cur.fetchone()[0]
        c.commit()
        return {"status": "ok", "id": str(new_id)}

@mcp.tool()
def get_employee(phone_no:str):
    """Get employee's data"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, age, department, salary, joining_date, phone_no FROM employees
                WHERE phone_no=%s
""",(phone_no,))
            row=cur.fetchone()
            if row is None:
                return{
                    "status":"error",
                    "message":"Employee not found"
                }
        conn.commit()
    return {
        "status": "ok",
        "id": str(row[0]),
        "name": row[1],
        "age": row[2],
        "department": str(row[3]) if row[3] else None,
        "salary": float(row[4]),
        "joining_date": str(row[5]) if row[5] else None,
        "phone_no": row[6],
    }


@mcp.tool()
def list_departments():
    """List all departments."""

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    department_name,
                    manager,
                    budget
                FROM departments
                ORDER BY department_name;
            """)

            rows = cur.fetchall()

    return [
        {
            "department": row[0],
            "manager": row[1],
            "budget": float(row[2])
        }
        for row in rows
    ]

@mcp.tool()
def department_statistics():
    """Get statistics for each department."""

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    d.department_name,
                    COUNT(e.id) AS total_employees,
                    COALESCE(SUM(e.salary),0) AS total_salary,
                    COALESCE(AVG(e.salary),0) AS average_salary
                FROM departments d
                LEFT JOIN employees e
                ON d.id = e.department
                GROUP BY d.department_name
                ORDER BY d.department_name;
            """)

            rows = cur.fetchall()

    return [
        {
            "department": row[0],
            "employees": row[1],
            "total_salary": float(row[2]),
            "average_salary": round(float(row[3]), 2)
        }
        for row in rows
    ]

@mcp.tool()
def average_salary(department_name: str):
    """Return the average salary of a department."""

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    AVG(e.salary)
                FROM employees e
                JOIN departments d
                ON e.department = d.id
                WHERE d.department_name = %s;
            """, (department_name,))

            row = cur.fetchone()

    if row is None or row[0] is None:
        return {
            "status": "error",
            "message": "Department not found or has no employees."
        }

    return {
        "department": department_name,
        "average_salary": round(float(row[0]), 2)
    }

if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=8000)