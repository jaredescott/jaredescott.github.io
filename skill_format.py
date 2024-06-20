skills_lists = [
    'Computer-aided Design, Mill Operation (including CNC), Lathe Operation, 3D Printing via Fused Deposition Modeling, Power Tools, Dynamic Systems & Controls, Soldering/Electronics, Circuit Design',
    'C++, Python, Julia, MATLAB, HTML, Javascript, Arduino, C, C#, Max, RISC-V, Verilog, Artificial Intelligence, Machine Learning, Computer Vision, Voice Recognition Systems, Multithreading, Quantum Computing, Microsoft Office, Web Development, SQL, Unity, XR Development, Unix, Git, Shell/bash, Algorithm Design',
    'Spanish as a Second Language, UX. Design, Audio Engineering, Tennis, Writing/Rhetoric, Music Analysis, Music Composition/Production and Performance (Piano, Violin, Electronic)'
]

import pdb

def format_skill(skill):
    r = f'- name: {skill}\n  weight: 1\n'
    return r

def format_skills(skills):
    r = ''
    for skill in skills:
        r += format_skill(skill) + '\n'
    return r

def main():
    for skills in skills_lists:
        print(format_skills(skills.split(', ')))
        pause = input('Press enter to continue...')
        print()

if __name__ == '__main__':
    main()
